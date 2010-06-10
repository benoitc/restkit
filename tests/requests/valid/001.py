request = {
    "method": "PUT",
    "uri": uri("/stuff/here?foo=bar"),
    "version": (1, 0),
    "headers": [
        ("Server", "http://127.0.0.1:5984"),
        ("Content-Type", "application/json"),
        ("Content-Length", "14")
    ],
    "body": '{"nom": "nom"}'
}