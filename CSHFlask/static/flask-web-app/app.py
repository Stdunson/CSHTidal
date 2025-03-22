from flask import Flask
from scripts.routes import main

app = Flask(__name__)
app.secret_key = b"\x91g\xcf\xe8x#g;\xb2\x9e\x9f\xeb\xa7\x9d'\x81m\x1a\xa9E\xd3\xcd\x01R"

app.register_blueprint(main)

if __name__ == '__main__':
    app.run(debug=True,port=5000)