from flask import Flask, redirect, url_for

from Testify.__init__ import reg_app

app = Flask(__name__)

app = reg_app()

@app.route('/')
def testify():
    return redirect(url_for('auth.index'))

if __name__ == '__main__':
    app.run(debug=True) 