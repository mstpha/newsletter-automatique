# 📰 Veille Thématique & Newsletter Automatique

**Sujet 05 — Séminaire Agents IA — Master MPDAM 2024-2025**  
*Domaine : Communication & Marketing*

---

## 🎯 Description

Pipeline multi-agents qui :
1. Récupère les **15 derniers articles** sur un thème via **NewsAPI**
2. Génère un **résumé de 3 phrases** par article via un LLM (Groq / LLaMA 3.3)
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
│   Groq → résumé       Top 5 sélect.      Objet email        │
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
- **Outil** : NewsAPI (`/v2/everything`, toutes langues)
- **LLM** : Groq (LLaMA 3.3 70B) — résumé en 3 phrases, ton journalistique
- **Output** : Liste JSON de 15 articles avec résumés

**Prompt clé Agent 1 :**
```
Resume cet article en exactement 3 phrases. Chaque phrase doit faire moins de 20 mots.
Reponds uniquement avec les 3 phrases, sans introduction ni commentaire.
```

### Agent 2 — Sélection & Ranking
- **Input** : liste de 15 articles résumés
- **LLM** : Groq (LLaMA 3.3 70B) — évaluation multi-critères
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
- **LLM** : Groq (LLaMA 3.3 70B) — génère introduction (2 phrases), CTA, objet email
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
- Compte [Groq](https://console.groq.com) (gratuit)
- Compte Gmail avec [App Password](https://myaccount.google.com/apppasswords)

### Installation des dépendances
```bash
pip install -r requirements.txt
```

### Configuration des clés API
Les clés sont directement définies dans `main.py` :
```python
NEWS_API_KEY   = "votre_cle_newsapi"
GROQ_API_KEY   = "votre_cle_groq"
GMAIL_USER     = "votre.adresse@gmail.com"
GMAIL_PASSWORD = "votre_app_password_gmail"
```

---

## 🚀 Exécution

### Lancement complet (avec envoi email)
```bash
python main.py "intelligence artificielle générative"
python main.py "cybersécurité"
python main.py "mobile development"
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
- **Format enforcement** : Contrainte du nombre de phrases (≤ 3) et de mots (≤ 20 par phrase)
- **Fallback robuste** : Nettoyage des backticks JSON avant parsing
- **Prompts sobres** : Ton neutre imposé pour éviter les formulations excessives

### Robustesse du Pipeline
- Try/catch sur l'envoi SMTP (log warning sans crash)
- Sauvegarde des JSONs intermédiaires à chaque étape
- Nettoyage automatique des réponses LLM (strip backticks)
- Recherche toutes langues pour maximiser les résultats

---


*Projet réalisé dans le cadre du Séminaire Agents IA — Master MPDAM 2024-2025*  
*Enseignant : Pr. Habib SMEI*