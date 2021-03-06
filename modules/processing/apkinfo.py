# Copyright (C) Check Point Software Technologies LTD.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.
import base64
import entropy
import hashlib
import logging
import os
import zipfile
from zipfile import BadZipfile

from lib.cuckoo.api.DexDumper.DexDumper import string_dumper
from lib.cuckoo.api.androguard_extentions import get_show_NativeMethods, get_show_CryptoCode, get_show_Permissions, \
    get_show_ReflectionCode, get_show_DynCode, get_methods, get_extended_receivers, get_permissions \
    # , get_receivers_info
from lib.cuckoo.api.certificate import get_certificate

try:
    from androguard.core.bytecodes.apk import APK
    from androguard.core.bytecodes.dvm import DalvikVMFormat
    from androguard.core.analysis.analysis import uVMAnalysis, PathVar, TAINTED_PACKAGE_CALL, is_crypto_code
    from androguard.core.analysis import analysis
    from androguard.core.bytecodes.dvm_permissions import DVM_PERMISSIONS
    HAVE_ANDROGUARD = True
except ImportError:
    HAVE_ANDROGUARD = False

from lib.cuckoo.common.abstracts import Processing
from lib.cuckoo.common.exceptions import CuckooProcessingError



def get_apk_icon(filepath):
    zfile = zipfile.ZipFile(filepath)
    for finfo in zfile.infolist():
        if "ic_launcher.png" in finfo.filename or "icon.png" in finfo.filename:
            ifile = zfile.open(finfo).read()
            return base64.encodestring(ifile)

    return None

log = logging.getLogger(__name__)


class ApkInfo(Processing):
    """Static android information about analysis session."""


    def __init__(self):
        self.key = "apkinfo"

        self.files_name_map={}
        self.files_name_map["apk"] = []
        self.files_name_map["jar"] = []
        self.files_name_map["so"] = []
        self.files_name_map["ko"] = []
        self.files_name_map["dex"] = []
        self.files_name_map["exe"] = []
        self.files_name_map["arm_exe"] = []

    def file_type_check(self, file):
        name = file["name"]
        fileName, fileExtension = os.path.splitext(name)
        type = file["type"]
        if "XML" in type:
            return False

        if "Java Jar" in type:
            self.files_name_map["jar"].append(file)
            if "apk" not in fileExtension and "jar" not in fileExtension:
                return True
        elif "Android" in type:
            self.files_name_map["apk"].append(file)
            if "apk" not in fileExtension and "jar" not in fileExtension:
                return True
        elif "shared object, ARM" in type:
            self.files_name_map["so"].append(file)
            if "so" not in fileExtension and "art" not in fileExtension:
                return True
        elif "executable, ARM" in type:
            self.files_name_map["arm_exe"].append(file)
            if "" != fileExtension:
                return True
        elif "relocatable, ARM" in type:
            self.files_name_map["ko"].append(file)
            if "ko" not in fileExtension:
                return True
        elif "Dalvik" in type:
            if file["name"] != "classes.dex":
                self.files_name_map["dex"].append(file)
            if "dex" not in fileExtension:
                return True
        elif "8086" in type or "PE32" in type:
            self.files_name_map["exe"].append(file)
            if "exe" not in fileExtension:
                return True
        else:
            if ".apk" == fileExtension:
                self.files_name_map["apk"].append(file)
            elif ".jar" == fileExtension:
                self.files_name_map["jar"].append(file)
            elif ".so" == fileExtension:
                self.files_name_map["so"].append(file)
            elif ".ko" == fileExtension:
                self.files_name_map["ko"].append(file)
            elif ".exe" == fileExtension:
                self.files_name_map["exe"].append(file)
            elif ".dex" == fileExtension:
                if file["name"] != "classes.dex":
                    self.files_name_map["dex"].append(file)

        return False

    def check_size(self, file_list):
        for file in file_list:
            if "classes.dex" in file["name"]:
                if "decompilation_threshold" in self.options:
                    if file["size"] < self.options.decompilation_threshold:
                        return True
                    else:
                        return False
                else:
                    return True
        return False

    def _apk_files(self, apk):
        """Returns a list of files in the APK."""
        ret = []
        for fname, filetype in apk.get_files_types().items():
            buf = apk.zip.read(fname)
            ret.append({
                "name": fname,
                "md5": hashlib.md5(buf).hexdigest(),
                "size": len(buf),
                "type": filetype,
            })
        return ret

    def find_encrypted_assets(self, apk):
        """Returns a dict of files in the APK assets that have high entropy."""
        ret = []
        for fname, filetype in apk.get_files_types().items():
            if "assets" in fname:
                if ".png" in fname and "png" in filetype.lower():
                    continue
                buf = apk.zip.read(fname)
                file_entropy = entropy.shannon_entropy(buf)
                if file_entropy > 0.9:
                    ret.append({
                        "name": fname,
                        "entropy": file_entropy,
                        "size": len(buf),
                        "type": filetype,
                    })
        return ret

    def _get_strings(self, apk_path):
        list_string = []
        for string in string_dumper(apk_path):
            try:
                list_string.append(str.decode(string, "utf-8"))
            except:
                pass

        return list_string

    def _scan_APKiD(self, input, timeout=60):
        try:
            import yara
            from apkid.apkid import get_rules, collect_files, do_yara, scan_apk
            rules = get_rules()
            results = {}
            for file_type, file_path in collect_files(input):
                try:
                    match_dict = do_yara(file_path, rules, timeout)
                    if len(match_dict) > 0:
                        results[file_path.split("/")[-1]] = match_dict
                    if 'zip' == file_type:
                        apk_matches = scan_apk(file_path, rules, timeout, True)
                        new_matches = {}
                        for key in apk_matches:
                            new_key = key.split("!")[1].replace(".", "_")
                            new_matches[new_key] = apk_matches[key]
                        results.update(new_matches)
                except yara.Error as e:
                    logging.error("error scanning: {}".format(e))
            return results
        except Exception as e:
            log.warning("APKiD failed: "+e.message)
            return {}

    def run(self):
        """Run androguard to extract static android information
                @return: list of static features
        """
        self.key = "apkinfo"
        apkinfo = {}

        if "file" not in self.task["category"] or not HAVE_ANDROGUARD:
            return

        #f = File(self.task["target"])
        #if f.get_name().endswith((".zip", ".apk")) or "zip" in f.get_type():
        if not os.path.exists(self.file_path):
            raise CuckooProcessingError("Sample file doesn't exist: \"%s\"" % self.file_path)

        apkinfo["APKiD"] = self._scan_APKiD(self.file_path)

        try:
            a = APK(self.file_path)
            if a.is_valid_APK():
                manifest = {}

                apkinfo["files"] = self._apk_files(a)
                apkinfo["encrypted_assets"] = self.find_encrypted_assets(a)
                manifest["package"] = a.get_package()
                apkinfo["hidden_payload"] = []

                for file in apkinfo["files"]:
                    if self.file_type_check(file):
                       apkinfo["hidden_payload"].append(file)

                apkinfo["files_flaged"] = self.files_name_map

                manifest["permissions"]= get_permissions(a)
                manifest["main_activity"] = a.get_main_activity()
                manifest["activities"] = a.get_activities()
                manifest["services"] = a.get_services()
                manifest["receivers"] = a.get_receivers()
                manifest["receivers_actions"] = get_extended_receivers(a)
                manifest["receivers_info"] = get_receivers_info(a)
                manifest["providers"] = a.get_providers()
                manifest["libraries"] = a.get_libraries()
                apkinfo["manifest"] = manifest

                apkinfo["icon"] = get_apk_icon(self.file_path)
                certificate = get_certificate(self.file_path)
                if certificate:
                    apkinfo["certificate"] = certificate


                #vm = DalvikVMFormat(a.get_dex())
                #strings = vm.get_strings()

                strings = self._get_strings(self.file_path)
                for subdir, dirs, files in os.walk(self.dropped_path):
                    for file in files:
                        path = os.path.join(subdir, file)
                        try:
                            extra_strings = self._get_strings(path)
                            strings = list(set(extra_strings + strings))
                        except:
                            pass

                apkinfo["dex_strings"] = strings

                static_calls = {}
                if self.options.decompilation:
                    if self.check_size(apkinfo["files"]):
                        vm = DalvikVMFormat(a.get_dex())
                        vmx = uVMAnalysis(vm)
                        # Be less verbose about androguard logging messages.
                        logging.getLogger("andro.runtime").setLevel(logging.CRITICAL)

                        static_calls["all_methods"] = get_methods(vmx)
                        static_calls["is_native_code"] = analysis.is_native_code(vmx)
                        static_calls["is_dynamic_code"] = analysis.is_dyn_code(vmx)
                        static_calls["is_reflection_code"] = analysis.is_reflection_code(vmx)
                        static_calls["is_crypto_code"] = is_crypto_code(vmx)

                        static_calls["dynamic_method_calls"] = get_show_DynCode(vmx)
                        static_calls["reflection_method_calls"] = get_show_ReflectionCode(vmx)
                        static_calls["permissions_method_calls"] = get_show_Permissions(vmx)
                        static_calls["crypto_method_calls"] = get_show_CryptoCode(vmx)
                        static_calls["native_method_calls"] = get_show_NativeMethods(vmx)

                        classes = list()
                        for cls in vm.get_classes():
                            classes.append(cls.name)

                        static_calls["classes"] = classes

                else:
                    log.warning("Dex size bigger than: %s",
                                self.options.decompilation_threshold)

                apkinfo["static_method_calls"] = static_calls

        except (IOError, OSError, BadZipfile) as e:
            raise CuckooProcessingError("Error opening file %s" % e)

        return apkinfo

