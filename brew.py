import os, platform, subprocess, dotbot, sys

class Brew(dotbot.Plugin):
    _brewDirective = "brew"
    _caskDirective = "cask"
    _tapDirective = "tap"
    _brewFileDirective = "brewfile"

    def can_handle(self, directive):
        return directive in (self._tapDirective, self._brewDirective, self._caskDirective, self._brewFileDirective)

    def handle(self, directive, data):
        if directive == self._tapDirective:
            self._bootstrap_brew()
            return self._tap(data)
        if directive == self._brewDirective:
            self._bootstrap_brew()
            return self._process_data("brew install", data)
        if directive == self._caskDirective:
            if sys.platform.startswith("darwin"):
                self._bootstrap_cask()
                return self._process_data("brew install --cask", data)
            else:
                return True
        if directive == self._brewFileDirective:
            self._bootstrap_brew()
            self._bootstrap_cask()
            return self._install_bundle(data)
        raise ValueError('Brew cannot handle directive %s' % directive)

    def _tap(self, tap_list):
        cwd = self._context.base_directory()
        log = self._log
        with open(os.devnull, 'w') as devnull:
            stdin = stdout = stderr = devnull
            for tap in tap_list:
                log.info("Tapping %s" % tap)
                cmd = "brew tap %s" % (tap)
                result = subprocess.call(cmd, shell=True, cwd=cwd)

                if result != 0:
                    log.warning('Failed to tap [%s]' % tap)
                    return False
            return True

    def _process_data(self, install_cmd, data):
        success = self._install(install_cmd, data)
        if success:
            self._log.info('All packages have been installed')
        else:
            self._log.error('Some packages were not installed')
        return success

    def _install(self, install_cmd, packages_list):
        cwd = self._context.base_directory()
        log = self._log
        all_success = True
        
        for package in packages_list:
            # Check if package is already installed
            if install_cmd == 'brew install':
                check_cmd = "brew ls --versions %s" % package
            else:
                # For casks, use the proper command to check if installed
                check_cmd = "brew list --cask %s 2>/dev/null || brew info --cask %s | grep -q 'Not installed'" % (package, package)
                
            with open(os.devnull, 'w') as devnull:
                is_installed = subprocess.call(check_cmd, shell=True, stdin=devnull, 
                                             stdout=devnull, stderr=devnull, cwd=cwd)
                
            if is_installed == 0:
                log.info("%s is already installed" % package)
                continue
                
            # If not installed, try to install it
            log.info("Installing %s" % package)
            cmd = "%s %s" % (install_cmd, package)
            
            # Capture the output to check for specific error patterns
            process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, cwd=cwd)
            stdout, stderr = process.communicate()
            result = process.returncode
            
            if result != 0:
                # Check for common "already installed" messages that might come with error codes
                stderr_str = stderr.decode('utf-8', errors='ignore') 
                stdout_str = stdout.decode('utf-8', errors='ignore')
                already_installed_msgs = [
                    "already installed",
                    "already exists", 
                    "is already installed",
                    "latest version already installed",
                    "already been downloaded"
                ]
                
                if any(msg in stderr_str or msg in stdout_str for msg in already_installed_msgs):
                    log.info("Application %s appears to be already installed, continuing..." % package)
                else:
                    log.warning('Failed to install [%s]' % package)
                    all_success = False
        
        return all_success

    def _install_bundle(self, brew_files):
        cwd = self._context.base_directory()
        log = self._log
        with open(os.devnull, 'w') as devnull:
            stdin = stdout = stderr = devnull
            for f in brew_files:
                log.info("Installing from file %s" % f)
                cmd = "brew bundle --file=%s" % f
                result = subprocess.call(cmd, shell=True, cwd=cwd)

                if result != 0:
                    log.warning('Failed to install file [%s]' % f)
                    return False
            return True

    def _bootstrap(self, cmd):
        with open(os.devnull, 'w') as devnull:
            stdin = stdout = stderr = devnull
            subprocess.call(cmd, shell=True, stdin=stdin, stdout=stdout, stderr=stderr,
                            cwd=self._context.base_directory())

    def _bootstrap_brew(self):
        link = "https://raw.githubusercontent.com/Homebrew/install/master/install.sh"
        cmd = """hash brew || /bin/bash -c "$(curl -fsSL {0})";
              brew update""".format(link)
        self._bootstrap(cmd)

    def _bootstrap_cask(self):
        self._bootstrap_brew()
        cmd = "brew tap caskroom/cask"
        self._bootstrap(cmd)
