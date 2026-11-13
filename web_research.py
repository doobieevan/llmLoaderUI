"""Explicit, bounded web-search/reference fetching utilities."""

import ipaddress
import re
import socket
import urllib.parse
import urllib.request
from html.parser import HTMLParser

MAX_HTML_BYTES = 1_000_000
USER_AGENT = "PocketGGUFCoder/0.1 (user-requested research)"


class SearchLinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            values = dict(attrs)
            href = values.get("href", "")
            classes = values.get("class", "")
            if href and ("result__a" in classes or "result" in classes):
                self.current = {"href": href, "text": []}

    def handle_data(self, data):
        if self.current is not None and data.strip():
            self.current["text"].append(data.strip())

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            href = self.current["href"]
            parsed = urllib.parse.urlparse(href)
            if parsed.hostname and "duckduckgo.com" in parsed.hostname:
                redirect = urllib.parse.parse_qs(parsed.query).get("uddg", [])
                href = urllib.parse.unquote(redirect[0]) if redirect else ""
            try:
                validate_http_url(href)
            except ValueError:
                href = ""
            title = " ".join(self.current["text"])
            if href and title:
                self.links.append((title, href))
            self.current = None


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg"):
            self.hidden += 1
        elif tag in ("p", "br", "div", "li", "h1", "h2", "h3", "article"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg") and self.hidden:
            self.hidden -= 1
        elif tag in ("p", "div", "li", "h1", "h2", "h3", "article"):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            text = data.strip()
            if text:
                self.parts.append(text + " ")


def validate_http_url(url, resolve_host=True):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Only public HTTP/HTTPS URLs without embedded credentials are supported.")
    hostname = parsed.hostname.rstrip(".").casefold()
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local"):
        raise ValueError("Local hostnames are not allowed for online reference fetches.")
    try:
        addresses = [ipaddress.ip_address(hostname)]
    except ValueError:
        if not resolve_host:
            return url
        try:
            addresses = [ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)]
        except (OSError, ValueError):
            raise ValueError("Reference host could not be resolved safely.") from None
    if not addresses or any(not address.is_global for address in addresses):
        raise ValueError("Only public internet addresses are allowed for fetched references.")
    return url


def search_url(query, engine="DuckDuckGo"):
    query = query.strip()
    if not query:
        raise ValueError("Enter a search query.")
    encoded = urllib.parse.quote_plus(query)
    engines = {
        "duckduckgo": f"https://html.duckduckgo.com/html/?q={encoded}",
        "google": f"https://www.google.com/search?q={encoded}",
        "bing": f"https://www.bing.com/search?q={encoded}",
        "dogpile": f"https://www.dogpile.com/serp?q={encoded}",
    }
    if engine.casefold() not in engines:
        raise ValueError("Unsupported search provider.")
    return engines[engine.casefold()]


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _safe_opener():
    opener = urllib.request.build_opener(_SafeRedirectHandler())
    opener.addheaders = [("User-Agent", USER_AGENT)]
    return opener


def fetch_search_results(query, timeout=12, max_bytes=MAX_HTML_BYTES):
    url = search_url(query, "DuckDuckGo")
    request = urllib.request.Request(url)
    with _safe_opener().open(request, timeout=timeout) as response:
        validate_http_url(response.geturl())
        raw = response.read(max_bytes + 1)
    parser = SearchLinkParser()
    parser.feed(raw[:max_bytes].decode("utf-8", errors="replace"))
    unique = []
    seen = set()
    for title, link in parser.links:
        if link not in seen:
            seen.add(link)
            unique.append((title, link))
        if len(unique) == 8:
            break
    return unique


def fetch_reference(url, timeout=12, max_bytes=MAX_HTML_BYTES):
    validate_http_url(url)
    opener = _safe_opener()
    request = urllib.request.Request(url)
    with opener.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        validate_http_url(final_url)
        content_type = response.headers.get("Content-Type", "")
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raw = raw[:max_bytes]
    charset_match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    charset = charset_match.group(1) if charset_match else "utf-8"
    text = raw.decode(charset, errors="replace")
    if "html" in content_type.lower() or "<html" in text[:1024].lower():
        parser = TextExtractor()
        parser.feed(text)
        text = "".join(parser.parts)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return final_url, text[:30000]
