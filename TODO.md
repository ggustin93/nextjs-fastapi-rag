# Plan: Deux Agents Spécialisés (Helpdesk + OTRS)

## Résumé

Création de **deux agents spécialisés** pour le support et l'analyse:

1. **@helpdesk** - Agent CdCO Osiris complet pour le support utilisateurs (citoyens et INI)
2. **@otrs** - Agent interne pour l'analyse de tickets OTRS

## Agent 1: @helpdesk (CdCO Osiris)

| Aspect | Valeur |
|--------|--------|
| **ID** | `helpdesk` |
| **Nom** | Centre de Compétence Osiris |
| **Icône** | 🏗️ |
| **Aliases** | `cdco`, `support` |
| **Température** | 0.5 |

### Outils Disponibles

| Outil | Usage |
|-------|-------|
| `search_knowledge_base` | Documentation Osiris, FAQ, procédures |
| `search_otrs_tickets` | Recherche de tickets similaires |
| `get_otrs_ticket` | Contexte de ticket existant |
| `get_worksite_info` | Informations chantier OSIRIS |

### System Prompt

System prompt CdCO complet fourni par l'utilisateur (bilingue FR/NL, périmètre strict, patterns de redirection).

---

## Agent 2: @otrs

| Aspect | Valeur |
|--------|--------|
| **ID** | `otrs` |
| **Nom** | OTRS Agent |
| **Icône** | 🎫 |
| **Aliases** | `tickets`, `otrs-agent` |
| **Température** | 0.3 |

### Outils Disponibles

| Outil | Usage |
|-------|-------|
| `search_otrs_tickets` | Recherche de tickets par critères |
| `get_otrs_ticket` | Détails d'un ticket spécifique |

### System Prompt

Prompt simple pour analyse interne:
- Analyse de patterns dans les tickets
- Recherche de tickets similaires
- Statistiques et tendances
- Support équipe interne (pas de contact direct citoyens)

---

## Fichiers à Créer/Modifier

| Fichier | Action | Description |
|---------|--------|-------------|
| `packages/core/agents/helpdesk_agent.py` | CREATE | Agent CdCO complet |
| `packages/core/agents/otrs_agent.py` | CREATE | Agent analyse tickets |
| `packages/core/agents/__init__.py` | EDIT | Enregistrer les deux agents |

---

## Implémentation

### Phase 1: Agent Helpdesk

**`packages/core/agents/helpdesk_agent.py`**:

```python
"""CdCO Osiris Helpdesk Agent.

Agent complet pour le support technique de la plateforme Osiris.
Bilingue FR/NL, périmètre strict avec redirections vers services compétents.
"""

from packages.core.agents import AgentConfig, register_agent

HELPDESK_SYSTEM_PROMPT = """
[System prompt CdCO complet - voir ci-dessous]
"""

HELPDESK_AGENT = AgentConfig(
    id="helpdesk",
    name="Centre de Compétence Osiris",
    icon="🏗️",
    system_prompt=HELPDESK_SYSTEM_PROMPT,
    enabled_tools=["search_knowledge_base", "search_otrs_tickets", "get_otrs_ticket", "get_worksite_info"],
    temperature=0.5,
    description="Helpdesk CdCO Osiris - Support citoyens et INI",
    aliases=["cdco", "support"],
)

register_agent(HELPDESK_AGENT)
```

### Phase 2: Agent OTRS

**`packages/core/agents/otrs_agent.py`**:

```python
"""OTRS Ticket Analyzer Agent.

Agent interne pour l'analyse de tickets OTRS.
Recherche de patterns, tickets similaires, statistiques.
"""

from packages.core.agents import AgentConfig, register_agent

OTRS_SYSTEM_PROMPT = """
Tu es un assistant d'analyse de tickets OTRS pour l'équipe interne du CdCO.

## Mission
- Analyser les tickets OTRS existants
- Identifier des patterns et tendances
- Trouver des tickets similaires
- Fournir des statistiques

## Règles
- Usage interne uniquement (pas de contact direct citoyens)
- Réponses concises et analytiques
- Focus sur les données et métriques
- Bilingue FR/NL selon la question

## Outils disponibles
- search_otrs_tickets: Recherche par critères (queue, état, date, texte)
- get_otrs_ticket: Détails complets d'un ticket

## Format de réponse
- Tableaux pour les résultats multiples
- Résumés exécutifs pour les analyses
- Liens vers les tickets pertinents
"""

OTRS_AGENT = AgentConfig(
    id="otrs-agent",
    name="OTRS Ticket Analyzer",
    icon="🎫",
    system_prompt=OTRS_SYSTEM_PROMPT,
    enabled_tools=["search_otrs_tickets", "get_otrs_ticket"],
    temperature=0.3,
    description="Analyse interne de tickets OTRS",
    aliases=["otrs", "tickets"],
)

register_agent(OTRS_AGENT)
```

### Phase 3: Enregistrer les agents

**`packages/core/agents/__init__.py`** - Ajouter imports:

```python
def _register_builtin_agents() -> None:
    if AGENTS:
        return
    from packages.core.agents import (
        rag_agent,
        weather_agent,
        helpdesk_agent,  # NEW
        otrs_agent,       # NEW
    )
```

---

## Usage

### @helpdesk (citoyens/INI)
```
@helpdesk Bonjour, je n'arrive plus à me connecter à Osiris
@cdco Ik krijg steeds een foutmelding
@support Comment créer un nouveau compte?
```

### @otrs (interne)
```
@otrs Trouve les tickets similaires au #12345
@otrs Quels sont les patterns de problèmes cette semaine?
@tickets Statistiques des tickets en attente
```

---

## System Prompt CdCO Complet

Le prompt fourni par l'utilisateur inclut:
1. Identité et mission CdCO (rattaché à Bruxelles Mobilité)
2. Périmètre strict (comptes, support technique, API, orientation)
3. Redirections (Guichet Osiris, Administration, Coordination)
4. Règles de communication bilingue FR/NL
5. Patterns de réponse standardisés
6. Contacts de référence (emails des services)
7. Gestion frustration et hors compétence
8. Signatures et formules de politesse

---

## Tests Manuels

### Helpdesk
1. `@helpdesk Je n'arrive plus à me connecter` → Diagnostic compte
2. `@cdco Ik krijg een foutmelding` → Réponse NL
3. `@support Prolonger mon autorisation` → Redirection Guichet

### OTRS Agent
1. `@otrs Tickets similaires au #12345` → Liste tickets
2. `@otrs Problèmes fréquents cette semaine` → Analyse patterns
3. `@tickets Queue "Support Technique" en attente` → Stats

---

## Estimation

| Tâche | Durée |
|-------|-------|
| Créer helpdesk_agent.py | 15 min |
| Créer otrs_agent.py | 10 min |
| Modifier __init__.py | 2 min |
| Tests manuels | 15 min |
| **Total** | **~40 min** |
