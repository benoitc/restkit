request = {
    "method": "GET",
    "uri": uri("/unusual_content_length"),
    "version": (1, 0),
    "headers": [
        ("conTENT-Length", "5")
    ],
    "body": "HELLO"
}