from flask import*
from openpyxl import*
import os


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods = ['POST'])
def login():
    
    if int(request.form['pass'])==1234 :
         print('success')


    return 'success'


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()



@app.route('/shutdown')
def shutdown():
    print('hey server')
    shutdown_server()
    return 'Server shutting down...'
        
    
    


if __name__ == "__main__":
    app.run()
