import os
import re
import shutil
import datetime
import urllib.parse
import yaml
import markdown
import jinja2

# Define workspace directories
DATA_DIR = os.path.join('src', 'data')
CONTENT_DIR = os.path.join('src', 'content')
TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'public'

# Try to import Markup for safe HTML injection in templates
try:
    from markupsafe import Markup
except ImportError:
    try:
        from jinja2 import Markup
    except ImportError:
        Markup = lambda x: x

ICONS_DIR = os.path.join('src', 'icons')
SVG_CACHE = {}

def load_svg_icons():
    cache = {}
    if os.path.exists(ICONS_DIR):
        for filename in os.listdir(ICONS_DIR):
            if filename.endswith('.svg'):
                name = os.path.splitext(filename)[0]
                filepath = os.path.join(ICONS_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        cache[name] = f.read()
                except Exception as e:
                    print(f"Error loading SVG {filepath}: {e}")
    return cache

SVG_CACHE.update(load_svg_icons())

def normalize_icon_name(name):
    if not name:
        return ""
    if name.endswith('.svg'):
        name = name[:-4]
    # Remove Font Awesome prefixes if present
    name = re.sub(r'^(fas|far|fab|fa)\s+fa-', '', name)
    name = re.sub(r'^fa-', '', name)
    return name.strip().lower()

def svg_icon_filter(icon_name, class_name="", style=""):
    norm_name = normalize_icon_name(icon_name)
    svg_content = SVG_CACHE.get(norm_name)
    if not svg_content:
        # On-demand fallback
        fallback_path = os.path.join(ICONS_DIR, f"{norm_name}.svg")
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    svg_content = f.read()
                    SVG_CACHE[norm_name] = svg_content
            except Exception:
                pass
                
    if not svg_content:
        print(f"Warning: Icon '{icon_name}' (normalized: '{norm_name}') not found in {ICONS_DIR}")
        return Markup(f"<!-- Icon '{icon_name}' not found -->")
        
    # Inject attributes into the root <svg> tag
    match = re.search(r'<svg([^>]*)>', svg_content, re.IGNORECASE)
    if not match:
        return Markup(svg_content)
        
    attrs_str = match.group(1)
    attrs = {}
    attr_pattern = re.compile(r'([\w\-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))')
    for attr_match in attr_pattern.finditer(attrs_str):
        k = attr_match.group(1).lower()
        v = attr_match.group(2) or attr_match.group(3) or attr_match.group(4)
        attrs[k] = v
        
    # Merge class
    merged_class = "svg-inline"
    if class_name:
        merged_class += f" {class_name}"
    if 'class' in attrs:
        existing_classes = attrs['class'].split()
        for c in existing_classes:
            if c not in merged_class.split():
                merged_class += f" {c}"
    attrs['class'] = merged_class
    
    # Merge style
    if style:
        if 'style' in attrs:
            attrs['style'] = attrs['style'].rstrip(';') + '; ' + style
        else:
            attrs['style'] = style
            
    # Standard properties for inline SVGs
    if 'aria-hidden' not in attrs:
        attrs['aria-hidden'] = 'true'
    if 'focusable' not in attrs:
        attrs['focusable'] = 'false'
    if 'role' not in attrs:
        attrs['role'] = 'img'
        
    new_attrs_str = ""
    for k, v in attrs.items():
        new_attrs_str += f' {k}="{v}"'
        
    new_svg_tag = f'<svg{new_attrs_str}>'
    updated_svg = svg_content[:match.start()] + new_svg_tag + svg_content[match.end():]
    return Markup(updated_svg)


def load_yaml(filepath):
    """Loads and returns YAML data from a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def parse_markdown_file(filepath):
    """Parses a markdown file with YAML frontmatter."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Frontmatter regex
    pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n(.*)$', re.DOTALL)
    match = pattern.match(content)
    if match:
        frontmatter_str = match.group(1)
        body_str = match.group(2)
        data = yaml.safe_load(frontmatter_str) or {}
        # Parse markdown body to HTML
        html_content = markdown.markdown(body_str)
        return data, html_content
    else:
        return {}, markdown.markdown(content)

def inline_list_icons(html_content, icon_name):
    """Finds all <li> tags and injects the SVG markup directly inside the <li> tag."""
    if not html_content:
        return html_content
    svg_markup = svg_icon_filter(icon_name)
    if not svg_markup:
        return html_content
    
    replacement = f'<li><span class="li-icon-inline">{svg_markup}</span>'
    return re.sub(r'<li>', replacement, html_content)

def get_collection(collection_name):
    """Reads a collection directory and parses its YAML files."""
    dirpath = os.path.join(CONTENT_DIR, collection_name)
    entries = []
    if not os.path.exists(dirpath):
        print(f"Warning: Collection directory {dirpath} does not exist.")
        return entries
    
    for filename in os.listdir(dirpath):
        if filename.endswith('.yaml'):
            filepath = os.path.join(dirpath, filename)
            data = load_yaml(filepath) or {}
            
            # Extract and parse the markdown body stored in the 'text' key
            raw_text = data.pop('text', '')
            html_content = markdown.markdown(raw_text) if raw_text else ''
            
            # Inline SVGs if applicable
            if collection_name == 'leistungen':
                html_content = inline_list_icons(html_content, 'check')
            elif collection_name == 'aktuelles':
                listen_icon = data.get('listenIcon')
                if listen_icon == 'chevron':
                    html_content = inline_list_icons(html_content, 'chevron-right')
                elif listen_icon == 'warnung':
                    html_content = inline_list_icons(html_content, 'exclamation-triangle')
            
            entry_id = os.path.splitext(filename)[0]
            entries.append({
                'id': entry_id,
                'data': data,
                'content': html_content
            })
    return entries

def get_base_path(route):
    """Calculates relative base path prefix based on the depth of the route."""
    route_stripped = route.strip('/')
    if not route_stripped:
        return '.'
    if '/' not in route_stripped and route_stripped.endswith('.html'):
        return '.'
    parts = [p for p in route_stripped.split('/') if p]
    if parts and parts[-1].endswith('.html'):
        depth = len(parts) - 1
    else:
        depth = len(parts)
    if depth == 0:
        return '.'
    return '/'.join(['..'] * depth)

def make_relative_nav(base_path, seiten):
    """Generates relative nav links dynamically from the seiten collection based on im_menue."""
    menu_items = []
    for entry_id, page in seiten.items():
        data = page['data']
        if data.get('im_menue', False):
            url = data.get('url')
            if url:
                href = url
            else:
                route = data.get('route', entry_id)
                if route == 'aktuelles' or route == 'index':
                    route = ''
                
                if route == '':
                    href = f"{base_path}/"
                else:
                    href = f"{base_path}/{route}/"
            
            menu_items.append({
                'label': data.get('menue_titel', data.get('titel', entry_id)),
                'href': href,
                'key': entry_id,
                'reihenfolge': data.get('reihenfolge', 99)
            })
            
    menu_items.sort(key=lambda x: x['reihenfolge'])
    return menu_items

def make_relative(path, base_path):
    """Normalize absolute paths with leading slash to be relative to base_path."""
    if isinstance(path, str) and path.startswith('/'):
        return f"{base_path}{path}"
    return path

def make_relative_size(path, base_path, size_suffix):
    """Generates relative path for a resized image suffix."""
    if not isinstance(path, str) or not path:
        return path
    clean_path = path.lstrip('/')
    root, ext = os.path.splitext(clean_path)
    new_path = f"{root}-{size_suffix}{ext}"
    if base_path == '.':
        return f"./{new_path}"
    return f"{base_path}/{new_path}"

def format_tel(value):
    """Formats a phone number for tel: links by removing spaces/dashes and prepending +49."""
    if not isinstance(value, str):
        return value
    clean = re.sub(r'[\s\-]', '', value)
    if clean.startswith('0'):
        clean = '+49' + clean[1:]
    return clean

def minify_css(css):
    """Removes comments and extraneous whitespace from CSS."""
    # Remove comments
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    # Remove whitespace around selectors/properties
    css = re.sub(r'\s*([\{\}:;,])\s*', r'\1', css)
    # Replace multiple spaces/newlines with a single space
    css = re.sub(r'\s+', ' ', css)
    return css.strip()

def minify_html(html):
    """Minifies HTML code while preserving the contents of <script> and <style> tags."""
    placeholders = []
    
    def placeholder_repl(match):
        placeholders.append(match.group(0))
        return f"<!--HTML_MINIFIER_PLACEHOLDER_{len(placeholders)-1}-->"
    
    # Temporarily extract script and style tags
    pattern = re.compile(r'<(script|style)\b[^>]*>.*?</\1>', re.DOTALL | re.IGNORECASE)
    html_with_placeholders = pattern.sub(placeholder_repl, html)
    
    # 1. Remove standard HTML comments (excluding our placeholders)
    comment_pattern = re.compile(r'<!--(?!HTML_MINIFIER_PLACEHOLDER_).*?-->', re.DOTALL)
    html_minified = comment_pattern.sub('', html_with_placeholders)
    
    # 2. Collapse consecutive whitespace characters
    html_minified = re.sub(r'\s+', ' ', html_minified)
    
    # 3. Remove whitespace between tags
    html_minified = re.sub(r'>\s+<', '><', html_minified)
    
    # Restore script and style tags
    for i, content in enumerate(placeholders):
        placeholder_str = f"<!--HTML_MINIFIER_PLACEHOLDER_{i}-->"
        html_minified = html_minified.replace(placeholder_str, content)
        
    return html_minified.strip()

def save_image_with_quality(src_path, dest_path, quality=80):
    """Saves an image with a specific compression quality (lossless optimize for PNG)."""
    from PIL import Image
    with Image.open(src_path) as img:
        if img.format == 'PNG':
            img.save(dest_path, 'PNG', optimize=True)
        else:
            img.save(dest_path, 'JPEG', quality=quality, optimize=True)

def resize_image_to_width(src_path, dest_path, target_width):
    """Resizes an image to a target width while keeping the aspect ratio."""
    from PIL import Image
    with Image.open(src_path) as img:
        w, h = img.size
        ratio = target_width / w
        new_w, new_h = target_width, int(h * ratio)
        resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        if img.format == 'PNG':
            resized_img.save(dest_path, 'PNG', optimize=True)
        else:
            resized_img.save(dest_path, 'JPEG', quality=80, optimize=True)

def process_images():
    """Reads raw images from src/uploads/ and generates required responsive widths."""
    src_uploads = os.path.join('src', 'uploads')
    dest_uploads = os.path.join('public', 'uploads')
    os.makedirs(dest_uploads, exist_ok=True)
    
    if not os.path.exists(src_uploads):
        print(f"Warning: Source uploads directory {src_uploads} does not exist.")
        return
        
    print("Processing uploads and generating responsive sizes...")
    for filename in os.listdir(src_uploads):
        src_path = os.path.join(src_uploads, filename)
        if not os.path.isfile(src_path) or filename.lower().endswith(('.yml', '.yaml', '.gitkeep', '.txt')):
            continue
            
        # Copy/recompress the original file to public/uploads/
        dest_orig_path = os.path.join(dest_uploads, filename)
        # Check if original needs to be copied/processed
        if not os.path.exists(dest_orig_path) or os.path.getmtime(src_path) > os.path.getmtime(dest_orig_path):
            try:
                save_image_with_quality(src_path, dest_orig_path, quality=80)
                print(f"Processed and compressed original: {filename}")
            except Exception as e:
                shutil.copy(src_path, dest_orig_path)
                print(f"Copied original (fallback): {filename}. Error: {e}")
        
        name, ext = os.path.splitext(filename.lower())
        
        # Determine image widths
        widths = []
        if name == 'header-bg':
            widths = [768, 1200, 1920]
        elif 'quadrat' in name:
            widths = [300, 600]
        elif name.startswith('galerie-'):
            widths = [300, 350, 600, 1000]
        elif name == 'map-placeholder':
            widths = [600, 1200]
        elif name == 'logo':
            widths = [525, 1050]
        elif name == 'mecum':
            widths = []
        elif name == 'praxis-7':
            widths = [310, 620]
        elif name in ['allgemein', 'angio', 'dermatologie', 'diabetologie', 'homoeopathie', 'innere', 'kardiologie', 'palliativ', 'reise', 'grippe', 'ernaehrungsmedizin']:
            widths = [400, 800, 1200]
        elif name in ['claudia-ertl', 'cornelia-reeb', 'elisabeth-schuler-hoetscher', 'gundula-bitterle', 'isabel-brand', 'katharina-ertl', 'ludwig-ertl', 'maria-betz', 'petra-vogel', 'sandra-sterzik', 'stephanie-hainz', 'veronika-weinmann']:
            widths = [190, 225, 380, 450]
        else:
            widths = [300, 600]
            
        for w in widths:
            dest_resized_name = f"{os.path.splitext(filename)[0]}-{w}w{os.path.splitext(filename)[1]}"
            dest_resized_path = os.path.join(dest_uploads, dest_resized_name)
            if not os.path.exists(dest_resized_path) or os.path.getmtime(src_path) > os.path.getmtime(dest_resized_path):
                try:
                    resize_image_to_width(src_path, dest_resized_path, w)
                    print(f"Generated resized image: {dest_resized_name}")
                except Exception as e:
                    print(f"Error resizing {filename} to {w}w: {e}")

def main():
    print("--- Starting Static Page Builder ---")
    
    # 0. Process images
    process_images()
    
    # 1. Load data
    print("Loading YAML data from src/data...")
    praxis = load_yaml(os.path.join(DATA_DIR, 'praxis.yaml'))
    ueber_uns = load_yaml(os.path.join(DATA_DIR, 'ueber-uns.yaml'))
    
    # 2. Load collections
    print("Loading content collections from src/content...")
    aerzte = sorted(get_collection('aerzte'), key=lambda x: x['data'].get('reihenfolge', 100))
    
    aktuelles_raw = get_collection('aktuelles')
    aktuelles = [e for e in aktuelles_raw if e['data'].get('sichtbar', True)]
    aktuelles = sorted(aktuelles, key=lambda x: x['data'].get('reihenfolge', 100))
    
    team = sorted(get_collection('team'), key=lambda x: x['data'].get('reihenfolge', 100))
    leistungen = sorted(get_collection('leistungen'), key=lambda x: x['data'].get('reihenfolge', 100))
    
    # Combined doctor + team photos for the carousel
    fotos = []
    for a in aerzte:
        if a['data'].get('foto'):
            fotos.append({'src': a['data']['foto'], 'alt': a['data'].get('foto_alt', a['data']['name'])})
    for t in team:
        if t['data'].get('foto'):
            fotos.append({'src': t['data']['foto'], 'alt': t['data'].get('foto_alt', t['data']['name'])})
            
    # Load pages from seiten collection
    seiten = {e['id']: e for e in get_collection('seiten')}
    
    # Load and minify CSS
    print("Loading and minifying CSS...")
    
    # 1. Font Awesome async CSS compilation is no longer needed (inline SVGs are used instead)

    # 2. Process essential CSS (Inlined directly in head)
    essential_css_content = ""
    src_css = os.path.join('src', 'styles', 'global.css')
    src_fonts_css = os.path.join('src', 'styles', 'font-faces.css')
    if os.path.exists(src_fonts_css):
        with open(src_fonts_css, 'r', encoding='utf-8') as f:
            essential_css_content += f.read() + "\n\n"
    if os.path.exists(src_css):
        with open(src_css, 'r', encoding='utf-8') as f:
            essential_css_content += f.read()
            
    minified_essential_css = minify_css(essential_css_content)

    # 3. Setup global context
    current_year = datetime.datetime.now().year
    maps_query = urllib.parse.quote_plus(f"{praxis['adresse']['strasse']}, {praxis['adresse']['ort']}")
    
    global_context = {
        'praxis': praxis,
        'ueber_uns': ueber_uns,
        'current_year': current_year,
        'aerzte': aerzte,
        'aktuelles': aktuelles,
        'team': team,
        'leistungen': leistungen,
        'fotos': fotos,
        'maps_query': maps_query,
        'global_css': minified_essential_css
    }
    
    # 4. Initialize Jinja2 environment
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(TEMPLATES_DIR))
    env.filters['rel'] = make_relative
    env.filters['rel_size'] = make_relative_size
    env.filters['tel'] = format_tel
    env.filters['svg_icon'] = svg_icon_filter
    
    # 5. Define page builds
    pages = []
    for entry_id, page_data in seiten.items():
        data = page_data['data']
        sichtbar = data.get('sichtbar', True)
        
        route = data.get('route', entry_id)
        if route == 'aktuelles' or route == 'index':
            route = ''
            
        # Determine target file path
        if route == '':
            target_path = os.path.join(OUTPUT_DIR, 'index.html')
        elif route.endswith('.html'):
            target_path = os.path.join(OUTPUT_DIR, route)
        else:
            target_path = os.path.join(OUTPUT_DIR, route)
            
        if not sichtbar:
            if os.path.exists(target_path):
                if os.path.isdir(target_path):
                    shutil.rmtree(target_path)
                    print(f"Deleted directory {target_path} because page is set to visible=false")
                else:
                    os.remove(target_path)
                    print(f"Deleted file {target_path} because page is set to visible=false")
            continue
            
        template_name = data.get('template')
        if not template_name:
            template_name = f"{entry_id}.twig"
            
        active_tab = data.get('active', entry_id)
        if route == '':
            active_tab = 'aktuelles'
            
        is_home_val = (route == '')
            
        pages.append({
            'route': route,
            'template': template_name,
            'context': {
                'title': data.get('meta_title', data.get('titel', '')),
                'description': data.get('meta_desc', ''),
                'active': active_tab,
                'is_home': is_home_val,
                **data
            }
        })
    
    # 6. Render static pages
    print("Rendering pages...")
    for page in pages:
        template = env.get_template(page['template'])
        route = page['route']
        base_path = get_base_path(route)
        nav = make_relative_nav(base_path, seiten)
        # Merge global context with page-specific context
        ctx = {
            **global_context,
            'base_path': base_path,
            'nav': nav,
            **page['context']
        }
        rendered_html = template.render(ctx)
        minified_html = minify_html(rendered_html)
        
        # Write to public/route/index.html or public/filename.html
        if page['route'] == '':
            target_file = os.path.join(OUTPUT_DIR, 'index.html')
        elif page['route'].endswith('.html'):
            target_file = os.path.join(OUTPUT_DIR, page['route'])
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
        else:
            target_dir = os.path.join(OUTPUT_DIR, page['route'])
            os.makedirs(target_dir, exist_ok=True)
            target_file = os.path.join(target_dir, 'index.html')
            
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(minified_html)
        print(f"Generated {target_file}")
        
    # 7. Render dynamic doctor bio pages
    print("Rendering doctor bio pages...")
    for arzt in aerzte:
        slug = arzt['id']
        route = f"praxisteam/{slug}"
        base_path = get_base_path(route)
        nav = make_relative_nav(base_path, seiten)
        template = env.get_template('arzt-detail.twig')
        
        # Build optimized custom descriptions for doctors
        name = arzt['data']['name']
        desc_src = arzt['data'].get('untertitel', arzt['data'].get('beschreibung', ''))
        bez = desc_src.split(',')[0] if desc_src else 'Fachärztin für Allgemeinmedizin'
        if "Ludwig" in name:
            desc = f"{name}, Facharzt für Innere Medizin und Kardiologie in Oberhaching. Erfahren Sie mehr über seine kardiologische Kompetenz & Erfahrung."
        elif "Claudia" in name:
            desc = f"{name} stellt sich vor: Fachärztin für Allgemeinmedizin und Akademische Lehrpraxis der LMU in Oberhaching. Lesen Sie ihre Vita!"
        elif "Veronika" in name:
            desc = f"{name}, Fachärztin für Allgemeinmedizin & Palliativmedizin in Oberhaching. Wir bieten fürsorgliche Begleitung für chronisch Kranke."
        else:
            desc = f"Erfahren Sie mehr über {name}, {bez} in Oberhaching. Vita, Ausbildung und Tätigkeitsschwerpunkte im Überblick."
            
        ctx = {
            **global_context,
            'base_path': base_path,
            'nav': nav,
            'title': f"{name} – Fach- und Hausarztpraxis Dres. Ertl",
            'description': desc,
            'active': 'praxisteam',
            'arzt': arzt
        }
        rendered_html = template.render(ctx)
        minified_html = minify_html(rendered_html)
        
        target_dir = os.path.join(OUTPUT_DIR, 'praxisteam', slug)
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, 'index.html')
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(minified_html)
        print(f"Generated {target_file}")
        
    # 8. Copy local fonts to output
    print("Copying local fonts...")

    # Copy font files
    src_fonts_dir = os.path.join('src', 'styles', 'fonts')
    dest_fonts_dir = os.path.join(OUTPUT_DIR, 'fonts')
    if os.path.exists(src_fonts_dir):
        if os.path.exists(dest_fonts_dir):
            shutil.rmtree(dest_fonts_dir)
        shutil.copytree(src_fonts_dir, dest_fonts_dir)
        print(f"Copied local font files to {dest_fonts_dir}")

    # Copy local SVG icons for CSS references
    dest_icons_dir = os.path.join(OUTPUT_DIR, 'svg-icons')
    if os.path.exists(ICONS_DIR):
        if os.path.exists(dest_icons_dir):
            shutil.rmtree(dest_icons_dir)
        shutil.copytree(ICONS_DIR, dest_icons_dir)
        print(f"Copied SVG icon files to {dest_icons_dir}")

    # 9. Copy PHP backend scripts and configuration files
    print("Copying PHP scripts and configs...")
    for filename in os.listdir('src'):
        if filename.endswith('.php') or filename == '.htaccess' or filename == 'robots.txt':
            src_file = os.path.join('src', filename)
            dest_file = os.path.join(OUTPUT_DIR, filename)
            shutil.copy(src_file, dest_file)
            print(f"Copied {src_file} to {dest_file}")

    print("--- Build completed successfully ---")

if __name__ == '__main__':
    main()
