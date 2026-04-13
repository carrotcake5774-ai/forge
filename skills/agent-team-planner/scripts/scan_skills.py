"""Scan installed skills and output inventory as JSON.

Usage:
    python .claude/skills/agent-team-planner/scripts/scan_skills.py [--root DIR]

Output: JSON array of skill objects with name, description, scripts, references.
"""
import sys
import os
import json
import re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from markdown text, handling multiline values."""
    match = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    current_key = None
    multiline_buf = []
    for line in match.group(1).split("\n"):
        stripped = line.strip()
        # New key-value pair (not indented continuation)
        if re.match(r"^[a-zA-Z_][\w-]*\s*:", line) and not line.startswith(" "):
            # Save previous multiline value
            if current_key and multiline_buf:
                fm[current_key] = " ".join(multiline_buf).strip()
                multiline_buf = []
            key, _, val = line.partition(":")
            current_key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val == ">" or val == "|":
                # Multiline YAML — collect following indented lines
                multiline_buf = []
            elif val:
                fm[current_key] = val
                current_key = None
        elif current_key and stripped:
            # Continuation of multiline value
            multiline_buf.append(stripped)
    # Flush last multiline
    if current_key and multiline_buf:
        fm[current_key] = " ".join(multiline_buf).strip()
    return fm


def scan_dir(skills_dir: Path) -> list:
    """Scan a skills directory for SKILL.md files."""
    results = []
    if not skills_dir.exists():
        return results

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            # Check for AGENT.md pattern
            agent_md = skill_dir / "AGENT.md"
            if not agent_md.exists():
                continue
            skill_md = agent_md

        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue

        fm = parse_frontmatter(text)
        name = fm.get("name", skill_dir.name)
        description = fm.get("description", "")

        # Collect scripts
        scripts_dir = skill_dir / "scripts"
        scripts = []
        if scripts_dir.exists():
            scripts = [f.name for f in scripts_dir.iterdir() if f.is_file()]

        # Collect references
        refs_dir = skill_dir / "references"
        references = []
        if refs_dir.exists():
            references = [f.name for f in refs_dir.iterdir() if f.is_file()]

        results.append({
            "name": name,
            "path": str(skill_dir.relative_to(skill_dir.parent.parent.parent)),
            "description": description[:200],
            "scripts": scripts,
            "references": references,
        })

    return results


def main():
    root = Path(sys.argv[sys.argv.index("--root") + 1]) if "--root" in sys.argv else None

    if root is None:
        # Auto-detect: walk up from script location to find project root
        # scripts/scan_skills.py -> agent-team-planner -> skills -> .claude -> project root
        script_dir = Path(__file__).resolve().parent
        root = script_dir.parent.parent.parent.parent

    # Scan global skills
    global_skills = root / ".claude" / "skills"
    inventory = scan_dir(global_skills)

    # Scan project-level agents
    for claude_dir in root.rglob(".claude"):
        agents_dir = claude_dir / "agents"
        if agents_dir.exists() and agents_dir.is_dir():
            for agent_dir in sorted(agents_dir.iterdir()):
                if agent_dir.is_dir():
                    agent_md = agent_dir / "AGENT.md"
                    if agent_md.exists():
                        try:
                            text = agent_md.read_text(encoding="utf-8")
                        except Exception:
                            continue
                        fm = parse_frontmatter(text)
                        inventory.append({
                            "name": fm.get("name", agent_dir.name),
                            "path": str(agent_dir.relative_to(root)),
                            "description": fm.get("description", "")[:200],
                            "type": "agent",
                            "scripts": [],
                            "references": [],
                        })

        # Also scan project-level skills
        proj_skills = claude_dir / "skills"
        if proj_skills.exists() and proj_skills != global_skills:
            for item in scan_dir(proj_skills):
                item["type"] = "project-skill"
                inventory.append(item)

    print(json.dumps(inventory, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
