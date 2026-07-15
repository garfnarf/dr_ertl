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

def make_relative_nav(base_path, terminland_url):
    """Generates relative nav links for base_path."""
    return [
        { 'label': 'Aktuelles', 'href': f"{base_path}/", 'key': 'aktuelles' },
        { 'label': 'Über Uns', 'href': f"{base_path}/ueber-uns/", 'key': 'ueber-uns' },
        { 'label': 'Praxisteam', 'href': f"{base_path}/praxisteam/", 'key': 'praxisteam' },
        { 'label': 'Leistungen', 'href': f"{base_path}/leistungen/", 'key': 'leistungen' },
        { 'label': 'Termine', 'href': terminland_url, 'key': 'termine' },
        { 'label': 'Anfahrt & Kontakt', 'href': f"{base_path}/kontakt/", 'key': 'kontakt' },
    ]

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
            widths = [550, 1100]
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
    
    # 1. Process and save non-essential Font Awesome CSS (Asynchronous)
    fa_files = [
        os.path.join(OUTPUT_DIR, 'fa', 'css', 'fontawesome.min.css'),
        os.path.join(OUTPUT_DIR, 'fa', 'css', 'solid.min.css'),
        os.path.join(OUTPUT_DIR, 'fa', 'css', 'regular.min.css'),
        os.path.join(OUTPUT_DIR, 'fa', 'css', 'brands.min.css')
    ]
    fa_css_content = ""
    for fa_file in fa_files:
        if os.path.exists(fa_file):
            with open(fa_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Inject font-display: optional; to satisfy Lighthouse font display requirements
                content = content.replace('@font-face{', '@font-face{font-display:optional;')
                content = content.replace('@font-face {', '@font-face {font-display:optional;')
                fa_css_content += content + "\n\n"
        else:
            print(f"Warning: Font Awesome file {fa_file} not found!")
            
    minified_fa_css = minify_css(fa_css_content)
    dest_fa_css = os.path.join(OUTPUT_DIR, 'fa', 'css', 'all-icons.min.css')
    os.makedirs(os.path.dirname(dest_fa_css), exist_ok=True)
    with open(dest_fa_css, 'w', encoding='utf-8') as f:
        f.write(minified_fa_css)
    print(f"Generated asynchronous icons CSS at {dest_fa_css}")

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
    
    # 5. Define page builds
    pages = [
        {
            'route': '',
            'template': 'index.twig',
            'context': {
                'title': 'Hausarzt Oberhaching – Hausarztpraxis Dres. Ertl',
                'description': 'Hausarztpraxis Dres. Ertl in Oberhaching. Allgemeinmedizin, Innere Medizin, Kindervorsorgen & offizielle Gelbfieberimpfstelle. Online-Termin buchen!',
                'active': 'aktuelles'
            }
        },
        {
            'route': 'ueber-uns',
            'template': 'ueber-uns.twig',
            'context': {
                'title': 'Über uns & Leistungen – Hausarztpraxis Dres. Ertl',
                'description': 'Lernen Sie unsere moderne Hausarztpraxis in Oberhaching kennen. Über 28 Jahre Erfahrung in Allgemeinmedizin, Kindervorsorge & Reisemedizin.',
                'active': 'ueber-uns'
            }
        },
        {
            'route': 'praxisteam',
            'template': 'praxisteam.twig',
            'context': {
                'title': 'Unser Praxisteam – Hausarztpraxis Dres. Ertl',
                'description': 'Das Ärzteteam und die medizinischen Fachangestellten der Praxis Dres. Ertl in Oberhaching stellen sich vor. Wir freuen uns darauf, Sie zu betreuen!',
                'active': 'praxisteam'
            }
        },
        {
            'route': 'leistungen',
            'template': 'leistungen.twig',
            'context': {
                'title': 'Leistungen, Reisemedizin & Vorsorge – Dres. Ertl',
                'description': 'Ihr Allgemeinarzt in Oberhaching: Leistungen wie Innere Medizin, Kardiologie, Diabetologie, Kindervorsorgen, Reisemedizin & Gelbfieberimpfstelle.',
                'active': 'leistungen'
            }
        },
        {
            'route': 'kontakt',
            'template': 'kontakt.twig',
            'context': {
                'title': 'Kontakt, Anfahrt & Sprechzeiten – Dres. Ertl',
                'description': 'Kontaktieren Sie die Hausarztpraxis Dres. Ertl in Oberhaching. Hier finden Sie Sprechzeiten, Telefonnummern, Anfahrtsskizze und Google Maps-Karte.',
                'active': 'kontakt'
            }
        },
        {
            'route': 'danke',
            'template': 'danke.twig',
            'context': {
                'title': 'Vielen Dank für Ihre Nachricht – Dres. Ertl',
                'description': 'Vielen Dank für Ihre Rezeptbestellung bei den Dres. Ertl in Oberhaching. Wir bearbeiten Ihre Anfrage umgehend zur Abholung in unserer Praxis.'
            }
        },
        {
            'route': 'datenschutz',
            'template': 'datenschutz.twig',
            'context': {
                'title': 'Datenschutzerklärung – Hausarztpraxis Dres. Ertl',
                'description': 'Datenschutzerklärung der Fach- und Hausarztpraxis Dres. Ertl in Oberhaching. Informationen zur DSGVO-konformen Verarbeitung Ihrer Daten auf unserer Website.',
                'titel': seiten['datenschutz']['data']['titel'] if 'datenschutz' in seiten else 'Datenschutz',
                'content': seiten['datenschutz']['content'] if 'datenschutz' in seiten else ''
            }
        },
        {
            'route': 'impressum',
            'template': 'impressum.twig',
            'context': {
                'title': 'Impressum – Fach- und Hausarztpraxis Dres. Ertl',
                'description': 'Gesetzliches Impressum der Fach- und Hausarztpraxis Dres. Ertl in Oberhaching. Kontaktdaten, Ärztekammer-Zugehörigkeit und rechtliche Angaben.',
                'titel': seiten['impressum']['data']['titel'] if 'impressum' in seiten else 'Impressum',
                'content': seiten['impressum']['content'] if 'impressum' in seiten else ''
            }
        },
        {
            'route': '404.html',
            'template': '404.twig',
            'context': {
                'title': 'Seite nicht gefunden – Fach- und Hausarztpraxis Dres. Ertl',
                'description': 'Die von Ihnen gesuchte Seite konnte leider nicht gefunden werden. Kehren Sie zurück zur Startseite.',
                'active': ''
            }
        }
    ]
    
    # 6. Render static pages
    print("Rendering pages...")
    for page in pages:
        template = env.get_template(page['template'])
        route = page['route']
        base_path = get_base_path(route)
        nav = make_relative_nav(base_path, praxis['terminland'])
        # Merge global context with page-specific context
        ctx = {
            **global_context,
            'base_path': base_path,
            'nav': nav,
            **page['context']
        }
        rendered_html = template.render(ctx)
        
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
            f.write(rendered_html)
        print(f"Generated {target_file}")
        
    # 7. Render dynamic doctor bio pages
    print("Rendering doctor bio pages...")
    for arzt in aerzte:
        slug = arzt['id']
        route = f"praxisteam/{slug}"
        base_path = get_base_path(route)
        nav = make_relative_nav(base_path, praxis['terminland'])
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
        
        target_dir = os.path.join(OUTPUT_DIR, 'praxisteam', slug)
        os.makedirs(target_dir, exist_ok=True)
        target_file = os.path.join(target_dir, 'index.html')
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
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

    # 9. Copy PHP backend scripts and configuration files
    print("Copying PHP scripts and configs...")
    for filename in os.listdir('src'):
        if filename.endswith('.php') or filename == '.htaccess':
            src_file = os.path.join('src', filename)
            dest_file = os.path.join(OUTPUT_DIR, filename)
            shutil.copy(src_file, dest_file)
            print(f"Copied {src_file} to {dest_file}")

    print("--- Build completed successfully ---")

if __name__ == '__main__':
    main()
