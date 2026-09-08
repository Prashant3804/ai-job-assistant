"""Deterministic Technology & Skill Extraction Module.

Extracts real, verifiable technical technologies from job titles and descriptions.
Filters out generic titles (e.g. 'Software Engineer', 'Developer') and company names.
"""

import re
from typing import List, Optional, Set

TECH_TAXONOMY = [
    # Programming Languages
    ("Python", [r"\bpython\b", r"\bpy3\b"]),
    ("JavaScript", [r"\bjavascript\b", r"\bjs\b", r"\becmascript\b"]),
    ("TypeScript", [r"\btypescript\b", r"\bts\b"]),
    ("Java", [r"\bjava\b"]),
    ("C++", [r"\bc\+\+\b", r"\bcpp\b"]),
    ("C#", [r"\bc\#\b", r"\bcsharp\b"]),
    ("C", [r"\bc\b"]),
    ("Go", [r"\bgolang\b", r"\bgo\b"]),
    ("Rust", [r"\brust\b"]),
    ("Ruby", [r"\bruby\b"]),
    ("PHP", [r"\bphp\b"]),
    ("Swift", [r"\bswift\b"]),
    ("Kotlin", [r"\bkotlin\b"]),
    ("Scala", [r"\bscala\b"]),
    ("SQL", [r"\bsql\b"]),
    ("R", [r"\br\b"]),
    ("Dart", [r"\bdart\b"]),
    ("Shell", [r"\bbash\b", r"\bshell\b", r"\bsh\b"]),

    # Frontend & Full Stack
    ("React", [r"\breact\b", r"\breactjs\b", r"\breact\.js\b"]),
    ("Next.js", [r"\bnext\.?js\b", r"\bnextjs\b"]),
    ("Vue.js", [r"\bvue\.?js\b", r"\bvue\b"]),
    ("Angular", [r"\bangular\b", r"\bangularjs\b"]),
    ("Node.js", [r"\bnode\.?js\b", r"\bnodejs\b", r"\bnode\b"]),
    ("TailwindCSS", [r"\btailwind\b", r"\btailwindcss\b"]),
    ("HTML", [r"\bhtml5?\b"]),
    ("CSS", [r"\bcss3?\b", r"\bsass\b", r"\bscss\b"]),
    ("Redux", [r"\bredux\b"]),
    ("GraphQL", [r"\bgraphql\b"]),
    ("REST APIs", [r"\brest\b", r"\brestful\b", r"\brest\s+apis?\b", r"\bapis?\b"]),
    ("WebSockets", [r"\bwebsockets?\b"]),

    # Backend & Web Frameworks
    ("FastAPI", [r"\bfastapi\b"]),
    ("Django", [r"\bdjango\b"]),
    ("Flask", [r"\bflask\b"]),
    ("Express", [r"\bexpress\.?js\b", r"\bexpress\b"]),
    ("Spring Boot", [r"\bspring\s+boot\b", r"\bspring\b"]),
    (".NET", [r"\b\.net\b", r"\bdotnet\b", r"\basp\.net\b"]),
    ("Ruby on Rails", [r"\brails\b", r"\bruby\s+on\s+rails\b"]),
    ("Laravel", [r"\blaravel\b"]),
    ("Microservices", [r"\bmicroservices?\b", r"\bmicro-services?\b"]),
    ("gRPC", [r"\bgrpc\b"]),

    # Databases & Caching
    ("PostgreSQL", [r"\bpostgres\b", r"\bpostgresql\b", r"\bpgsql\b"]),
    ("MySQL", [r"\bmysql\b"]),
    ("MongoDB", [r"\bmongodb\b", r"\bmongo\b"]),
    ("Redis", [r"\bredis\b"]),
    ("Cassandra", [r"\bcassandra\b"]),
    ("DynamoDB", [r"\bdynamodb\b"]),
    ("Elasticsearch", [r"\belasticsearch\b"]),
    ("SQLite", [r"\bsqlite\b"]),
    ("Snowflake", [r"\bsnowflake\b"]),
    ("Kafka", [r"\bkafka\b"]),
    ("RabbitMQ", [r"\brabbitmq\b"]),

    # Cloud & DevOps
    ("AWS", [r"\baws\b", r"\bamazon\s+web\s+services\b"]),
    ("Azure", [r"\bazure\b", r"\bmicrosoft\s+azure\b"]),
    ("GCP", [r"\bgcp\b", r"\bgoogle\s+cloud\b"]),
    ("Docker", [r"\bdocker\b"]),
    ("Kubernetes", [r"\bkubernetes\b", r"\bk8s\b"]),
    ("Terraform", [r"\bterraform\b"]),
    ("CI/CD", [r"\bci\/cd\b", r"\bci-cd\b", r"\bcontinuous\s+integration\b"]),
    ("GitHub Actions", [r"\bgithub\s+actions\b"]),
    ("Linux", [r"\blinux\b", r"\bunix\b"]),
    ("Git", [r"\bgit\b"]),

    # AI, ML & Data Science
    ("Machine Learning", [r"\bmachine\s+learning\b", r"\bml\b"]),
    ("Deep Learning", [r"\bdeep\s+learning\b"]),
    ("PyTorch", [r"\bpytorch\b"]),
    ("TensorFlow", [r"\btensorflow\b"]),
    ("scikit-learn", [r"\bscikit-learn\b", r"\bsklearn\b"]),
    ("Pandas", [r"\bpandas\b"]),
    ("NumPy", [r"\bnumpy\b"]),
    ("NLP", [r"\bnlp\b", r"\bnatural\s+language\s+processing\b"]),
    ("LLM", [r"\bllms?\b", r"\blarge\s+language\s+models?\b"]),
    ("Computer Vision", [r"\bcomputer\s+vision\b", r"\bopencv\b"]),
    ("Data Engineering", [r"\bdata\s+engineering\b", r"\betl\b", r"\bdata\s+pipelines?\b"]),
    ("Spark", [r"\bapache\s+spark\b", r"\bspark\b"]),

    # Security & Infrastructure
    ("Security", [r"\bcybersecurity\b", r"\bapplication\s+security\b", r"\bappsec\b", r"\binformation\s+security\b", r"\bsecurity\s+engineering\b"]),
    ("Cloud Infrastructure", [r"\bcloud\s+infrastructure\b", r"\binfrastructure\b"]),
]

GENERIC_BLACKLIST = {
    "software engineering",
    "software engineer",
    "senior software engineer",
    "staff software engineer",
    "lead software engineer",
    "principal software engineer",
    "backend engineer",
    "frontend engineer",
    "full stack engineer",
    "fullstack engineer",
    "developer",
    "senior developer",
    "engineer",
    "intern",
    "software developer",
    "engineering",
    "tech",
    "technology",
    "it",
    "team",
    "company",
    "stripe",
    "coinbase",
    "elastic",
    "coupa",
    "figma",
    "cloudflare",
    "reddit",
    "datadog",
    "dropbox",
    "lemon.io",
    "lemon",
    "postman",
    "gitlab",
    "applicant",
    "candidate",
    "experience",
    "skills",
    "work",
    "job",
}

def extract_technologies(
    title: Optional[str] = "",
    description: Optional[str] = "",
    existing_skills: Optional[List[str]] = None,
    max_skills: int = 15
) -> List[str]:
    combined_text = f"{title or ''} {description or ''}".lower()
    extracted_skills: List[str] = []
    seen_canonical: Set[str] = set()

    title_lower = (title or "").lower()
    for canonical, patterns in TECH_TAXONOMY:
        for pat in patterns:
            if pat in [r"\bc\b", r"\br\b", r"\bgo\b"]:
                if re.search(r"\b(c\s+programming|language\s+c|c\/c\+\+|golang)\b", title_lower):
                    if canonical not in seen_canonical:
                        extracted_skills.append(canonical)
                        seen_canonical.add(canonical)
                        break
            elif re.search(pat, title_lower):
                if canonical not in seen_canonical:
                    extracted_skills.append(canonical)
                    seen_canonical.add(canonical)
                    break

    for canonical, patterns in TECH_TAXONOMY:
        if canonical in seen_canonical:
            continue
        for pat in patterns:
            if pat in [r"\bc\b", r"\br\b"]:
                if re.search(r"\b(c\s+programming|c\s+language|c\/c\+\+|r\s+programming)\b", combined_text):
                    extracted_skills.append(canonical)
                    seen_canonical.add(canonical)
                    break
            elif re.search(pat, combined_text):
                extracted_skills.append(canonical)
                seen_canonical.add(canonical)
                break

    if existing_skills:
        for s in existing_skills:
            clean_s = s.strip()
            lower_s = clean_s.lower()
            if not clean_s or lower_s in GENERIC_BLACKLIST:
                continue

            mapped = False
            for canonical, patterns in TECH_TAXONOMY:
                for pat in patterns:
                    if re.search(pat, lower_s):
                        if canonical not in seen_canonical:
                            extracted_skills.append(canonical)
                            seen_canonical.add(canonical)
                        mapped = True
                        break
                if mapped:
                    break

            if not mapped and len(clean_s) >= 2 and lower_s not in GENERIC_BLACKLIST:
                if clean_s.title() not in seen_canonical:
                    extracted_skills.append(clean_s.title())
                    seen_canonical.add(clean_s.title())

    if not extracted_skills:
        if "frontend" in title_lower or "react" in title_lower:
            extracted_skills = ["JavaScript", "TypeScript", "React", "HTML", "CSS"]
        elif "backend" in title_lower or "api" in title_lower:
            extracted_skills = ["Python", "REST APIs", "SQL", "PostgreSQL", "Docker"]
        elif "full" in title_lower and ("stack" in title_lower or "stack" in title_lower):
            extracted_skills = ["JavaScript", "Python", "React", "SQL", "REST APIs"]
        elif "data" in title_lower or "analytics" in title_lower:
            extracted_skills = ["Python", "SQL", "Data Engineering", "Pandas"]
        elif "devops" in title_lower or "cloud" in title_lower or "sre" in title_lower:
            extracted_skills = ["Docker", "Kubernetes", "Linux", "CI/CD", "AWS"]
        elif "machine learning" in title_lower or "ai" in title_lower:
            extracted_skills = ["Python", "Machine Learning", "PyTorch", "NumPy"]
        else:
            extracted_skills = ["Python", "SQL", "Git", "REST APIs"]

    return extracted_skills[:max_skills]
