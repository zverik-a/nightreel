# AUR package

1. Push a tag `vX.Y.Z`; the release workflow builds the GitHub release.
2. Here: set `pkgver`, reset `pkgrel=1`, run `updpkgsums`, then `makepkg -si` to test.
3. `makepkg --printsrcinfo > .SRCINFO`
4. Copy `PKGBUILD` and `.SRCINFO` into your clone of `ssh://aur@aur.archlinux.org/nightreel.git`, commit, push.
