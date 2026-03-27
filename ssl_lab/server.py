from flask import Flask, jsonify
import ssl

app = Flask(__name__)

@app.route('/stocks-data.json')
def get_data():
    return jsonify({
        "stocks": [
            {"name": "Apple", "price": 180},
            {"name": "Tesla", "price": 250}
        ]
    })

if __name__ == '__main__':
    # Меняй здесь True/False для проверки pinning
    use_bad_cert = False  # <-- False = сертификат A, True = сертификат B

    if use_bad_cert:
        cert = 'certB.pem'
        key = 'keyB.pem'
    else:
        cert = 'certA.pem'
        key = 'keyA.pem'

    context = (cert, key)

    app.run(host='127.0.0.1', port=5000, ssl_context=context)