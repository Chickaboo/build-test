# Managing virtual environments

I assume your virtual environment is created (or linked) to .venv
This is the project standard.

I manage my environments with [direnv](https://thelinuxcode.com/managing-per-directory-environment-variables-effortlessly-with-direnv/)

if you wanna be like me:
[here](https://direnv.net/docs/installation.html)

direnv is packaged for a variety of systems:

    Fedora
    Arch Linux
    Debian
    Gentoo Guru
    NetBSD pkgsrc-wip
    NixOS
    macOS Homebrew
    openSUSE
    MacPorts
    Ubuntu
    GNU Guix
    Windows


I have included my .envrc in the git root in the hope that it
is useful it simply activates the python virtual environment
in .venv
if it exists. Else creates one and activates it.
```
# Create venv if needed
if [[ ! -d .venv ]]; then
    echo "Creating virtual environment..."
    python -m venv .venv
fi

# Activate environment
source .venv/bin/activate
```
