# Profil seccomp

`seccomp_profile.json` vient du dépôt Microsoft Playwright, commit
`8124fc39233c4c349b9dbebd4abc4103738eae81` :
https://github.com/microsoft/playwright/blob/8124fc39233c4c349b9dbebd4abc4103738eae81/utils/docker/seccomp_profile.json

SHA-256 : `cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`.
Licence Apache 2.0 reproduite dans `LICENSE.playwright`.

Il autorise les opérations de namespaces nécessaires au sandbox Chromium,
sans utiliser `privileged` ni `seccomp=unconfined`. Le navigateur s'exécute
avec un utilisateur non-root et `chromium_sandbox=True`.
Voir https://playwright.dev/python/docs/docker.
