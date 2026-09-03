from wsgiref.simple_server import make_server

from app.application import application


if __name__ == "__main__":
    with make_server("127.0.0.1", 8080, application) as server:
        print("Backend läuft auf http://127.0.0.1:8080")
        server.serve_forever()
