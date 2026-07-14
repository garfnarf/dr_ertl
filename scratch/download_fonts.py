import os
import re
import urllib.request

URL = "https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300;0,400;0,600;0,700;1,300;1,400;1,600;1,700&family=Roboto:ital,wght@0,400;0,500;1,400;1,500&display=swap"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36"
}

def main():
    print("Fetching font stylesheet from Google...")
    req = urllib.request.Request(URL, headers=HEADERS)
    with urllib.request.urlopen(req) as response:
        css_content = response.read().decode('utf-8')
    
    # Create local directories
    fonts_dir = os.path.join("src", "styles", "fonts")
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Parse URLs
    urls = re.findall(r'url\((https://[^\)]+)\)', css_content)
    print(f"Found {len(urls)} font files to download.")
    
    # Download files and map names
    url_to_local = {}
    for i, url in enumerate(urls):
        filename = url.split('/')[-1]
        local_path = os.path.join(fonts_dir, filename)
        
        print(f"Downloading {i+1}/{len(urls)}: {filename}")
        req_file = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req_file) as f_res:
            with open(local_path, 'wb') as out_f:
                out_f.write(f_res.read())
        
        # Keep relative URL format for global.css: url('fonts/filename.woff2')
        url_to_local[url] = f"url('fonts/{filename}')"

    # Replace remote URLs in the CSS content with local references
    def replace_url(match):
        full_url = match.group(1)
        return url_to_local.get(full_url, match.group(0))

    local_css = re.sub(r'url\((https://[^\)]+)\)', replace_url, css_content)
    
    # Output the generated CSS to font-faces.css
    output_css_path = os.path.join("src", "styles", "font-faces.css")
    with open(output_css_path, "w", encoding="utf-8") as out_f:
        out_f.write(local_css)
        
    print(f"Successfully generated local font files in {fonts_dir} and CSS declarations in {output_css_path}")

if __name__ == "__main__":
    main()
