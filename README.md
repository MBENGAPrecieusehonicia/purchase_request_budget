# Demandes d'achat internes — `purchase_request_budget`

Module Odoo qui gère les demandes d'achat internes d'une entreprise
multi-départements : de l'expression du besoin par un employé jusqu'à la
génération des demandes de prix fournisseurs, avec une validation qui dépend
du montant et un contrôle du budget de chaque département.

---

## 1. Installation

| Élément | Valeur |
|---|---|
| Version d'Odoo | **Odoo 19 Community** |
| Dépendances | `base`, `mail`, `hr`, `purchase`, `product` (aucun module tiers) |
| Licence | LGPL-3 |

1. Copier le dossier `purchase_request_budget` dans un dossier d'addons
   (ici `C:/odoo/custom_addons`) et l'ajouter au paramètre `addons_path` du
   fichier de configuration d'Odoo.
2. Installer le module :

   ```bash
   # Base avec données de démonstration
   python odoo-bin -c odoo.conf -d ma_base -i purchase_request_budget --with-demo

   # Base sans données de démonstration
   python odoo-bin -c odoo.conf -d ma_base -i purchase_request_budget
   ```

3. Mettre à jour le module après une modification du code :

   ```bash
   python odoo-bin -c odoo.conf -d ma_base -u purchase_request_budget
   ```

Sous Windows, avec l'installeur officiel d'Odoo 19, `python` est le Python
fourni par Odoo (`...\Odoo\python\python.exe`) et `odoo-bin` se trouve dans
`...\Odoo\server\`.

### Comptes de démonstration

Avec les données de démo, le mot de passe de chaque compte est identique à
son identifiant.

| Identifiant | Rôle | Département |
|---|---|---|
| `admin` | Direction (+ administrateur Achats) | — |
| `directeur` | Direction | — |
| `manager_it` | Manager | Informatique |
| `manager_rh` | Manager | Ressources humaines |
| `manager_log` | Manager | Logistique |
| `employe_it` | Demandeur | Informatique |
| `employe_rh` | Demandeur | Ressources humaines |
| `employe_log` | Demandeur | Logistique |
| `acheteur` | Acheteur (Achats / Utilisateur) | — |

---

## 2. Présentation

### Ce que fait le module

- **Demande d'achat** numérotée automatiquement (`DA/2026/0001`) : demandeur,
  département, dates, motif, lignes d'articles avec prix estimé et
  fournisseur suggéré, total calculé.
- **Workflow en 6 états** : Brouillon → Soumise → (Attente Direction) →
  Validée → Convertie, et Refusée.
- **Validation à deux niveaux** : le manager du département valide toujours ;
  la Direction valide en plus si le total dépasse un seuil paramétrable par
  société.
- **Contrôle budgétaire** : chaque département a un budget par période ;
  une demande qui dépasse le budget restant ne peut pas être soumise.
- **Génération des demandes de prix** : une demande de prix par fournisseur,
  reliée à la demande d'origine.

### Parcours d'un utilisateur, étape par étape

1. **La Direction crée le budget** du département
   (*Achats > Demandes internes > Budgets*) : département, période, montant alloué.
2. **L'employé crée sa demande** (*Achats > Demandes internes > Mes demandes*) :
   son nom et son département sont pré-remplis ; il saisit le motif et les
   articles. Le prix et le fournisseur sont proposés depuis la fiche produit.
3. **Il clique sur « Soumettre »** : Odoo vérifie qu'il y a au moins une ligne
   et que le budget restant du département suffit. Sinon, un message indique
   le total de la demande et le budget restant. Une activité « À valider »
   est créée pour le manager.
4. **Le manager valide** (*Demandes à valider*) :
   - total ≤ seuil → la demande passe à **Validée** ;
   - total > seuil → elle passe à **Attente Direction**, et une activité est
     créée pour la Direction, qui la valide à son tour.
5. **Refus possible à chaque niveau** : une fenêtre oblige à saisir un motif,
   affiché sur la demande et publié dans le chatter ; le demandeur est notifié.
   Il peut alors **remettre la demande en brouillon**, la corriger et la soumettre
   à nouveau.
6. **L'acheteur clique sur « Créer les demandes de prix »** : une demande de
   prix est créée par fournisseur suggéré. La demande passe à **Convertie** ;
   un bouton affiche le nombre de demandes de prix liées, et chaque demande
   de prix affiche la demande d'achat d'origine.

### Paramétrage

*Achats > Configuration > Paramètres*, bloc « Commandes » :
**Seuil de validation Direction** (5 000 par défaut, propre à chaque société).

---

## 3. Choix techniques

### Structure du module

```
purchase_request_budget/
├── __manifest__.py                 Carte d'identité du module
├── models/
│   ├── purchase_request.py         Demande : champs, calculs, workflow, action planifiée
│   ├── purchase_request_line.py    Lignes de la demande
│   ├── purchase_request_budget.py  Budget de département
│   ├── purchase_order.py           Lien demande de prix -> demande d'origine
│   ├── res_company.py              Seuil Direction par société
│   └── res_config_settings.py      Seuil dans l'écran Paramètres
├── wizard/                         Assistant « motif de refus »
├── security/                       Groupes, règles de visibilité, droits d'accès
├── data/                           Séquence, type d'activité, action planifiée
├── views/                          Écrans et menus
└── demo/                           Données de démonstration
```

### Modèle de données

| Modèle | Type | Rôle |
|---|---|---|
| `purchase.request` | nouveau | En-tête de la demande, workflow, chatter |
| `purchase.request.line` | nouveau | Lignes (produit, quantité, prix, fournisseur) |
| `purchase.request.budget` | nouveau | Budget d'un département sur une période |
| `purchase.request.refuse.wizard` | nouveau (temporaire) | Saisie du motif de refus |
| `purchase.order` | hérité | + champ `purchase_request_id` (demande d'origine) |
| `res.company` | hérité | + champ `purchase_request_threshold` (seuil) |
| `res.config.settings` | hérité | Affiche le seuil dans les paramètres |

Relations : une demande a plusieurs lignes (One2many) ; une demande a
plusieurs demandes de prix (One2many via `purchase_request_id`) ; le budget
est retrouvé par département + date (pas de lien stocké).

### Décisions et justifications

- **Seuil stocké sur la société** (`res.company`) et affiché via un champ
  `related` dans les paramètres : c'est la méthode standard d'Odoo pour un
  réglage « par société » (le module Achats fait pareil pour sa double validation).
- **Montants engagé et restant non stockés** : ils dépendent de l'état de
  toutes les demandes du département ; les recalculer à l'affichage garantit
  qu'ils sont toujours justes. Le calcul se fait en `sudo()` pour inclure les
  demandes que l'utilisateur ne voit pas.
- **Total de la demande stocké** (`store=True`), comme demandé, pour pouvoir le
  sommer dans les listes et dans le calcul des budgets.
- **Verrouillage hors brouillon** : la méthode `write()` refuse toute
  modification d'une demande qui n'est plus en brouillon. Les méthodes du
  workflow passent un contexte `purchase_request_workflow=True` pour pouvoir
  changer l'état. Les vues rendent aussi les champs en lecture seule, mais la
  règle est appliquée côté serveur (une vue seule ne protège pas).
- **Contrôles métier côté Python** (et pas seulement en cachant les boutons) :
  qui peut valider, interdiction de valider sa propre demande, etc. Un bouton
  caché n'empêche pas un appel direct au serveur.
- **Activités Odoo standard** (`mail.activity`) pour « À valider » : le manager
  les voit dans son horloge d'activités, sans développement d'écran supplémentaire.
- **Demande de prix créée avec les prix et la description de la demande**, pour
  que l'acheteur parte de l'estimation ; Odoo calcule ensuite les taxes.
- **Contraintes** : chevauchement des budgets en `@api.constrains` (règle à
  plusieurs enregistrements) ; montant alloué positif en contrainte SQL
  (`models.Constraint`, syntaxe d'Odoo 19).

### Sécurité

| Groupe | Hérite de | Demandes visibles | Budgets |
|---|---|---|---|
| Demandeur | Utilisateur interne | Les siennes | Lecture |
| Manager | Demandeur | Les siennes + celles de son département | Lecture |
| Direction | Manager | Toutes | Lecture, création, modification, suppression |
| Acheteur (Achats / Utilisateur, standard) | — | Validées et converties | Lecture |

- **Droits d'accès** (`security/ir.model.access.csv`) : *quelles opérations* un
  groupe peut faire sur un modèle.
- **Règles d'enregistrement** (`security/purchase_request_security.xml`) :
  *quels enregistrements* il voit. Elles s'additionnent quand un utilisateur
  est dans plusieurs groupes. Des règles multi-sociétés s'appliquent à tous.
- Le menu Achats est ouvert au groupe Demandeur ; ses sous-menus standards
  (Commandes, Produits) sont réservés aux acheteurs, pour qu'un employé ne
  voie que « Demandes internes ».

### Action planifiée

Une fois par jour, les demandes en attente de validation depuis plus de
3 jours reçoivent un message qui notifie les valideurs attendus.

---

## 4. Hypothèses

Points non précisés dans le cahier des charges et choix retenus :

1. **Demandeur = manager de son département** : il ne peut pas valider sa
   propre demande ; c'est donc la Direction qui la valide au niveau 1 (elle
   reçoit l'activité). Même chose si le département n'a pas de manager.
2. **Personne ne valide sa propre demande**, Direction comprise.
3. **Refuser** demande les mêmes droits que valider au même niveau.
4. **Remise en brouillon** : par le demandeur (ou la Direction). Le motif de
   refus reste affiché pour la correction et est effacé à la nouvelle soumission.
5. **Le contrôle budgétaire n'a lieu qu'à la soumission**, comme indiqué au §3.4 ;
   il n'est pas refait à la validation.
6. **Budget utilisé** : celui du département de la demande dont la période
   contient la **date de la demande**.
7. **Fournisseur suggéré par défaut** : le premier fournisseur de la fiche
   produit (modifiable sur la ligne).
8. **Date prévue des demandes de prix** : la date souhaitée de la demande, ou
   la date du jour si elle est vide.
9. **Seuil Direction par défaut** : 5 000 dans la devise de la société.
10. **Un demandeur ne peut créer une demande qu'à son nom** (la règle de
    visibilité s'applique aussi à la création).

---

## 5. Limites et suite

- Le budget n'est pas re-vérifié à la validation : deux demandes soumises en
  même temps peuvent, une fois validées, dépasser le budget. Amélioration :
  refaire le contrôle à la validation finale.
- Les montants engagés ne tiennent pas compte des prix réels des demandes de
  prix (seulement des prix estimés).
- Pas de prise en charge des sous-départements (un manager ne voit pas les
  demandes des départements enfants).
- Bonus non réalisés : rapport PDF « Bon de demande d'achat » et assistant de
  choix du fournisseur pour les lignes qui n'en ont pas. Réalisé : couleur des
  lignes de liste selon l'état.
- Pas de tests automatisés : à ajouter (`tests/`) pour le workflow, le budget
  et les droits d'accès.
