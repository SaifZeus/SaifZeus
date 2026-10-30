import os
import json
import urllib.request
import urllib.error

TOKEN = os.environ.get("METRICS_TOKEN") or os.environ.get("GITHUB_TOKEN")

GRAPHQL_URL = "https://api.github.com/graphql"

QUERY = """
query {
  viewer {
    login
    name
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        name
        isPrivate
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node {
              name
              color
            }
          }
        }
        stargazerCount
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      totalPullRequestContributions
      totalIssueContributions
    }
  }
}
"""

def fetch_data():
    if not TOKEN:
        raise ValueError("METRICS_TOKEN is not set.")
    
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=json.dumps({"query": QUERY}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "SaifZeus-Stats-Generator"
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        if "errors" in data:
            raise RuntimeError(data["errors"])
        return data["data"]["viewer"]

def generate_languages_svg(viewer, output_path="dist/top-langs.svg"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    lang_totals = {}
    lang_colors = {}
    
    # Language color fallbacks
    default_colors = {
        "Python": "#3572A5",
        "HTML": "#e34c26",
        "JavaScript": "#f1e05a",
        "CSS": "#563d7c",
        "SQL": "#e38c00",
        "PLpgSQL": "#336791",
        "PostgreSQL": "#336791"
    }
    
    for repo in viewer["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            size = edge["size"]
            color = edge["node"]["color"] or default_colors.get(name, "#38bdae")
            
            # Skip Jupyter Notebook bulk data
            if name == "Jupyter Notebook":
                continue
                
            lang_totals[name] = lang_totals.get(name, 0) + size
            lang_colors[name] = color

    total_bytes = sum(lang_totals.values())
    if total_bytes == 0:
        total_bytes = 1
        
    sorted_langs = sorted(lang_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Calculate widths for the progress bar
    progress_rects = []
    current_x = 0
    total_bar_width = 300
    
    for name, b in sorted_langs:
        pct = (b / total_bytes)
        w = round(pct * total_bar_width, 1)
        if w > 0:
            color = lang_colors.get(name, "#38bdae")
            progress_rects.append(f'<rect x="{current_x}" y="0" width="{w}" height="8" fill="{color}"/>')
            current_x += w

    bars_svg = "\n      ".join(progress_rects)
    
    # Legend items
    legend_items = []
    # 2 items per row
    row_y = [25, 45, 65]
    for i, (name, b) in enumerate(sorted_langs):
        pct = (b / total_bytes) * 100
        color = lang_colors.get(name, "#38bdae")
        col_x = 0 if i % 2 == 0 else 160
        y = row_y[i // 2] if (i // 2) < len(row_y) else 85
        legend_items.append(f'''
      <g transform="translate({col_x}, {y})">
        <circle cx="5" cy="5" r="4.5" fill="{color}"/>
        <text x="16" y="9" class="lang-text">{name} <tspan class="lang-pct">{pct:.1f}%</tspan></text>
      </g>''')

    legends_svg = "".join(legend_items)
    
    svg = f"""<svg width="350" height="160" viewBox="0 0 350 160" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #70a5fd; }}
    .lang-text {{ font: 500 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #e2e8f0; }}
    .lang-pct {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: #94a3b8; }}
  </style>
  <rect x="0.5" y="0.5" width="349" height="159" rx="15" fill="#1a1b27" stroke="#2a2b3d"/>
  
  <g transform="translate(25, 30)">
    <text x="0" y="0" class="header">Most Used Languages</text>
  </g>

  <g transform="translate(25, 50)">
    <mask id="bar-mask">
      <rect x="0" y="0" width="300" height="8" rx="4" fill="white"/>
    </mask>
    <g mask="url(#bar-mask)">
      {bars_svg}
    </g>
    
    <g transform="translate(0, 5)">
      {legends_svg}
    </g>
  </g>
</svg>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated {output_path}")

def generate_stats_svg(viewer, output_path="dist/stats.svg"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    contribs = viewer["contributionsCollection"]
    total_commits = contribs["totalCommitContributions"] + contribs["restrictedContributionsCount"]
    total_prs = contribs["totalPullRequestContributions"]
    total_issues = contribs["totalIssueContributions"]
    
    total_stars = sum(repo["stargazerCount"] for repo in viewer["repositories"]["nodes"])
    
    svg = f"""<svg width="400" height="160" viewBox="0 0 400 160" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: #70a5fd; }}
    .stat-label {{ font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #94a3b8; }}
    .stat-value {{ font: 700 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #38bdae; }}
    .rank-circle {{ stroke: #70a5fd; stroke-width: 5; fill: none; }}
    .rank-text {{ font: 800 22px 'Segoe UI', Ubuntu, Sans-Serif; fill: #38bdae; }}
  </style>
  <rect x="0.5" y="0.5" width="399" height="159" rx="15" fill="#1a1b27" stroke="#2a2b3d"/>

  <g transform="translate(25, 30)">
    <text x="0" y="0" class="header">Saif Wael's GitHub Stats</text>
  </g>

  <!-- Stats Rows -->
  <g transform="translate(25, 52)">
    <g transform="translate(0, 0)">
      <text x="0" y="10" class="stat-label">Total Commits (All Repos):</text>
      <text x="210" y="10" class="stat-value">{total_commits}</text>
    </g>
    <g transform="translate(0, 24)">
      <text x="0" y="10" class="stat-label">Total Stars Earned:</text>
      <text x="210" y="10" class="stat-value">{total_stars}</text>
    </g>
    <g transform="translate(0, 48)">
      <text x="0" y="10" class="stat-label">Total PRs:</text>
      <text x="210" y="10" class="stat-value">{total_prs}</text>
    </g>
    <g transform="translate(0, 72)">
      <text x="0" y="10" class="stat-label">Total Issues Opened:</text>
      <text x="210" y="10" class="stat-value">{total_issues}</text>
    </g>
  </g>

  <!-- Rank Badge -->
  <g transform="translate(325, 85)">
    <circle cx="0" cy="0" r="32" class="rank-circle" stroke-opacity="0.2"/>
    <circle cx="0" cy="0" r="32" class="rank-circle" stroke-dasharray="200" stroke-dashoffset="40"/>
    <text x="0" y="8" text-anchor="middle" class="rank-text">A+</text>
  </g>
</svg>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated {output_path}")

if __name__ == "__main__":
    try:
        viewer = fetch_data()
        generate_languages_svg(viewer)
        generate_stats_svg(viewer)
    except Exception as e:
        print(f"Error generating stats: {e}")
