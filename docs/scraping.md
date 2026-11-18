# Pratiques de scraping

## Choisir le mode par site

Commence par vérifier si les données sont déjà dans le HTML, un export ou une API
documentée. Le mode HTTP fait moins de requêtes qu'un navigateur. Si JavaScript
est indispensable, active Playwright sur les seules requêtes concernées avec
`meta={"playwright": True}`. Le spider `quotes` illustre les deux modes.

Un navigateur automatisé reste détectable. Les outils « stealth », la rotation
aléatoire de User-Agent et les proxys publics ne constituent pas une garantie.
Ce projet privilégie un comportement stable et un volume limité.

## Rythme et sessions

La configuration autorise une requête Scrapy à la fois par domaine. Le délai de
base de 3 secondes varie de ±50 %, donc ce n'est pas un minimum strict de 3 secondes.
AutoThrottle démarre à 5 secondes et adapte le rythme jusqu'à 60 secondes selon
la latence. Augmente les délais si un site le demande ; ne réduis pas tout à zéro
pour gagner quelques minutes.

Une seule page Playwright par contexte est ouverte à la fois. Le contexte par
défaut conserve les cookies pendant un crawl, avec locale et fuseau constants.
Il est éphémère : un nouveau lancement repart avec une session neuve. Pour une
session authentifiée autorisée, utilise les mécanismes Playwright `storage_state`
ou un contexte persistant, et conserve ces fichiers hors de Git. Ne mélange pas
plusieurs comptes dans le même contexte.

Le navigateur conserve son User-Agent natif, cohérent avec sa version installée.
Les requêtes HTTP ont une identité explicite et stable, configurable dans `.env`.
Les règles robots sont évaluées pour `tcg-scraping`, sans se faire passer pour un
robot de moteur de recherche.

## Limites propres au navigateur

AutoThrottle et `robots.txt` portent sur les requêtes gérées par Scrapy.
Les sous-requêtes du navigateur (scripts, XHR/fetch, iframes, redirections internes)
ne passent pas toutes par l'ordonnanceur Scrapy : une navigation peut générer
beaucoup de trafic malgré `CONCURRENT_REQUESTS_PER_DOMAIN=1`.

Le prédicat `abort_unneeded_resource` bloque images, médias et polices. Adapte-le
au site : un média peut être nécessaire à certaines données. Les scripts et XHR
restent actifs. Pour un futur spider marchand, examine les domaines et endpoints
appelés et limite les ressources au besoin, après avoir vérifié leur rôle.

Utilise `PageMethod` pour les interactions avec le navigateur, et attends un
élément précis. N'utilise pas de longues temporisations arbitraires. Dans l'exemple,
l'attente se termine aussi si Chromium signale un statut de navigation >=400,
afin de laisser le middleware traiter immédiatement un 403/429. Le plugin ferme
les pages automatiquement ; `playwright_include_page` reste désactivé.

## Réagir à un refus

Sur 403/429, le middleware arrête le crawl entier et journalise `blocked_403`
ou `blocked_429`. Sur 429, il affiche la valeur brute de `Retry-After`, en secondes
ou sous forme de date selon le serveur. **Il ne reprend pas automatiquement** :
respecte au moins ce délai et vérifie la cause avant de relancer.

Des requêtes déjà en vol peuvent finir pendant la fermeture. Le statut d'arrêt
se trouve dans `finish_reason` des statistiques Scrapy ; un code de sortie 0
ne signifie pas à lui seul que l'extraction est complète.

Seules certaines erreurs temporaires (500, 502, 503, 504, 522, 524, 408 et erreurs
réseau prévues par Scrapy) font l'objet de deux réessais maximum. Le rythme reste
encadré par AutoThrottle ; ce projet n'ajoute pas de backoff exponentiel personnalisé.

Une réponse 200 peut aussi contenir un challenge ou une page de connexion.
L'exemple s'arrête avec `unexpected_content` si les citations attendues manquent,
ou `request_failed` si l'attente du navigateur échoue. Ce n'est pas un détecteur
universel de CAPTCHA : chaque spider doit vérifier la structure et les données.

## Cache, limites et exports

Le cache HTTP est désactivé par défaut pour éviter des prix périmés. Active
`HTTP_CACHE=true` pendant la mise au point de pages publiques : durée d'une heure,
stockage local dans `.scrapy/httpcache`. Les pages Playwright et les réponses de
blocage ne sont pas mises en cache. Ne réutilise pas un cache entre comptes.

Chaque crawl de démonstration est borné par `max_pages`. Le filtrage des doublons
Scrapy empêche les boucles sur une même URL. Pour un nouveau spider, définis ses
domaines autorisés et ses limites de pages, d'items et de durée.

Les exports JSONL, caches, `.env`, cookies et outils locaux sont ignorés par Git.
Les exports du Makefile remplacent le fichier existant. Pour conserver un historique,
passe un autre chemin avec la commande Scrapy `-o`/`-O` et un nom daté.

## Adapter à un marchand TCG

1. Vérifier les règles publiées et les possibilités d'API/export du site.
2. Créer un spider dans `tcg_scraper/spiders/`, avec ses domaines autorisés.
3. Définir des champs stables : identifiant, nom, édition, langue, état, prix,
   devise, disponibilité, URL et date de collecte.
4. Tester les sélecteurs sur des fixtures HTML locales, y compris une page vide,
   un prix manquant et une page de challenge.
5. Commencer par une page et examiner les statistiques, puis augmenter prudemment.

## Références

- [AutoThrottle](https://docs.scrapy.org/en/latest/topics/autothrottle.html)
- [Réglages Scrapy](https://docs.scrapy.org/en/latest/topics/settings.html)
- [Middleware robots, retries et cache](https://docs.scrapy.org/en/latest/topics/downloader-middleware.html)
- [Intégration scrapy-playwright](https://github.com/scrapy-plugins/scrapy-playwright)
- [Playwright dans Docker](https://playwright.dev/python/docs/docker)
