# 📰 Veille Thématique & Newsletter Automatique

**Sujet 05 — Séminaire Agents IA — Master MPDAM 2024-2025**  
*Domaine : Communication & Marketing*

---

## 🎯 Description

Pipeline multi-agents qui :
1. Récupère les **15 derniers articles** sur un thème via **NewsAPI**
2. Génère un **résumé de 3 phrases** par article via un LLM (Claude)
3. **Note et sélectionne les 5 meilleurs** articles (score 0–10 justifié)
4. Rédige une **newsletter HTML** professionnelle via un template Jinja2
5. Génère un **objet email accrocheur** et envoie via **Gmail SMTP**

---

## 🏗️ Architecture des Agents

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE PRINCIPAL                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   AGENT 1   │    │   AGENT 2   │    │   AGENT 3   │     │
│  │  Collecte & │───▶│  Sélection  │───▶│  Rédaction  │     │
│  │   Résumé    │    │  & Ranking  │    │  Newsletter │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│        │                  │                   │             │
│   NewsAPI (15 arts)   Score 0-10          Jinja2 HTML       │
│   Claude → résumé     Top 5 sélect.      Objet email        │
│        │                  │                   │             │
│        ▼                  ▼                   ▼             │
│  articles_bruts.json  top5_selectionnes.json  ┌──────────┐ │
│                                               │  ACTION  │ │
│                                               │  Gmail   │ │
│                                               │  SMTP    │ │
│                                               └──────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Agent 1 — Collecte & Résumé
- **Input** : mot-clé thématique
- **Outil** : NewsAPI (`/v2/everything`, langue FR puis EN en fallback)
- **LLM** : Prompt de résumé → 3 phrases max, ton journalistique
- **Output** : Liste JSON de 15 articles avec résumés

**Prompt clé Agent 1 :**
```
Tu es un journaliste expert. Résume l'article ci-dessous en EXACTEMENT 3 phrases
concises et informatives. Ne dépasse pas 3 phrases. Réponds uniquement avec le résumé.
```

### Agent 2 — Sélection & Ranking
- **Input** : liste de 15 articles résumés
- **LLM** : Évaluation multi-critères (actualité, profondeur, intérêt pro)
- **Output** : Scores JSON + justifications, Top 5 trié

**Prompt clé Agent 2 :**
```
Attribue un score 0-10 selon :
- Actualité et nouveauté (0-3 pts)
- Profondeur et valeur informative (0-4 pts)
- Intérêt pour un public professionnel (0-3 pts)
Réponds UNIQUEMENT avec un JSON valide.
```

### Agent 3 — Rédaction Newsletter
- **Input** : Top 5 articles scorés
- **LLM** : Génère introduction (3-4 phrases), CTA, objet email
- **Template** : Jinja2 (`newsletter.html.j2`)
- **Output** : HTML complet + objet email

---

## 📁 Structure du Projet

```
newsletter_agent/
├── main.py                    # Pipeline principal (3 agents)
├── generate_sample.py         # Génération exemple sans API keys
├── requirements.txt           # Dépendances Python
├── templates/
│   └── newsletter.html.j2     # Template Jinja2 réutilisable
├── output/
│   ├── newsletter_exemple.html      # Exemple de newsletter générée ✅
│   ├── top5_selectionnes.json       # Top 5 articles scorés ✅
│   └── articles_bruts.json          # Articles bruts (généré au runtime)
└── README.md                  # Ce fichier
```

---

## ⚙️ Installation

### Prérequis
- Python 3.10+
- Compte [NewsAPI](https://newsapi.org) (gratuit)
- Clé API [Anthropic](https://console.anthropic.com)
- Compte Gmail avec [App Password](https://myaccount.google.com/apppasswords)

### Installation des dépendances
```bash
pip install -r requirements.txt
```

### Configuration des variables d'environnement
```bash
export NEWS_API_KEY="votre_cle_newsapi"
export ANTHROPIC_API_KEY="votre_cle_anthropic"
export GMAIL_USER="votre.adresse@gmail.com"
export GMAIL_PASSWORD="votre_app_password_gmail"
export RECIPIENT_EMAIL="destinataire@email.com"
```

---

## 🚀 Exécution

### Lancement complet (avec envoi email)
```bash
python main.py "intelligence artificielle générative"
python main.py "cybersécurité"
python main.py "transition énergétique"
```

### Sans envoi email (mode preview)
```bash
python main.py "blockchain" --no-email
```

### Générer un exemple sans API keys
```bash
python generate_sample.py
# → output/newsletter_exemple.html
```

---

## 📤 Exemple de Sortie JSON (Agent 2)

```json
[
  {
    "id": 0,
    "score": 10,
    "justification": "Annonce majeure très récente, intérêt direct pour les professionnels IA."
  },
  {
    "id": 3,
    "score": 9,
    "justification": "Impact réglementaire direct sur les entreprises européennes."
  }
]
```

---

## 📊 Critères de Scoring (Agent 2)

| Critère | Poids | Description |
|---------|-------|-------------|
| Actualité & Nouveauté | 0–3 pts | Article publié récemment, annonce inédite |
| Profondeur Informative | 0–4 pts | Analyse, données, expertise réelle |
| Intérêt Professionnel | 0–3 pts | Utilité pour un public B2B ou académique |
| **TOTAL** | **0–10** | Seuil sélection : Top 5 |

---

## 🎨 Qualité du Prompt Engineering

### Techniques utilisées
- **Output contraint** : JSON strict sans markdown pour l'Agent 2
- **Chain-of-thought** : Critères explicites avec sous-scores pour le ranking
- **Persona assignment** : "journaliste expert", "éditeur de newsletter"
- **Format enforcement** : Contrainte du nombre de phrases (≤ 3)
- **Fallback robuste** : Nettoyage des backticks JSON avant parsing
- **Temperature implicite** : Prompts précis → sorties déterministes

### Robustesse du Pipeline
- Fallback langue EN si aucun article FR trouvé
- Try/catch sur l'envoi SMTP (log warning sans crash)
- Sauvegarde des JSONs intermédiaires à chaque étape
- Nettoyage automatique des réponses LLM (strip backticks)

---

## 📋 Livrables

| Livrable | Fichier | Statut |
|----------|---------|--------|
| Script Python 3 agents | `main.py` | ✅ |
| Template Jinja2 réutilisable | `templates/newsletter.html.j2` | ✅ |
| Newsletter HTML générée | `output/newsletter_exemple.html` | ✅ |
| JSON Top 5 scorés | `output/top5_selectionnes.json` | ✅ |
| README + instructions | `README.md` | ✅ |

---

## 🔐 Sécurité

> ⚠️ Ne jamais committer les clés API dans le code source.  
> Utiliser des variables d'environnement ou un fichier `.env` (ajouté à `.gitignore`).

```bash
# .env (ne pas committer)
NEWS_API_KEY=xxx
ANTHROPIC_API_KEY=xxx
GMAIL_PASSWORD=xxx
```

---

*Projet réalisé dans le cadre du Séminaire Agents IA — Master MPDAM 2024-2025*  
*Enseignant : Pr. Habib SMEI*
