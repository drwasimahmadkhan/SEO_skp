from app.services.extractor import extract_page


def test_empty_meta_vs_missing():
    html_empty = """
    <html><head>
      <title>Books</title>
      <meta name="description" content="">
    </head><body><h1>Books</h1></body></html>
    """
    data = extract_page(html_empty, "https://example.com/")
    assert data["meta_description_present"] is True
    assert data["meta_description"] == ""

    html_missing = """
    <html><head><title>Books</title></head>
    <body><h1>Books</h1></body></html>
    """
    data2 = extract_page(html_missing, "https://example.com/")
    assert data2["meta_description_present"] is False


def test_strip_title_and_schema():
    html = """
    <html><head>
      <title>  Hello World  </title>
      <script type="application/ld+json">{"@type":"Organization","name":"Acme"}</script>
    </head><body><h1>Hi</h1><img src="/a.png"></body></html>
    """
    data = extract_page(html, "https://example.com/")
    assert data["title"] == "Hello World"
    assert data["schema_jsonld"][0]["@type"] == "Organization"
    assert data["images"][0]["alt_missing"] is True
