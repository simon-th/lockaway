import smartcar
import json
from geopy import distance
from flask import Flask, redirect, request, jsonify, render_template, g
from flask_cors import CORS
from werkzeug.utils import secure_filename

import os

import requests

app = Flask(__name__)
CORS(app)

azure = 'azure tags: '

UPLOAD_FOLDER = app.root_path + '/static'
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
UPLOAD_FILE = None
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# global variable to save our access_token
access = None
latitude = 30.2882467
longitude = -97.7375051
vehicle_global = None
analysis = None


# global variable to save credentials
credentials = json.load(open('credentials.json'))
user = json.load(open('user.json'))

subscription_key = "86795bebaaee4d89a0b665a08dba9539"
assert subscription_key

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def imageKeyMatch(key):
    global analysis
    result = False
    for tag in analysis['tags']:
        if tag['name'] == key and tag['confidence'] >= 0.5:
            result = True
    return result


def isCloseEnough(lat_car, lon_car, lat_u, lon_u, radius):
    car = (lat_car, lon_car)
    user = (lat_u, lon_u)
    dist = 1000*distance.vincenty(car, user).km
    return dist < radius

client = smartcar.AuthClient(
    client_id = credentials['CLIENT_ID'],
    client_secret = credentials['CLIENT_SECRET'],
    redirect_uri = credentials['REDIRECT_URI'],
    scope = ['read_vehicle_info', 'control_security', 'control_security:unlock', 'control_security:lock', 'read_location'],
    test_mode=True
)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global UPLOAD_FILE
    image_path = None
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            UPLOAD_FILE = filename
            global subscription_key
            vision_base_url = "https://southcentralus.api.cognitive.microsoft.com/vision/v2.0/"
            analyze_url = vision_base_url + "analyze"
            image_path = UPLOAD_FOLDER + "/" + UPLOAD_FILE
            image_data = open(image_path, "rb").read()
            headers = {'Ocp-Apim-Subscription-Key': subscription_key,
                        'Content-Type': 'application/octet-stream'}
            params = {'visualFeatures': 'Tags'}
            response = requests.post(
                analyze_url, headers=headers, params=params, data=image_data)
            response.raise_for_status()
            global analysis
            analysis = response.json()
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            for tag in analysis['tags']:
                global azure
                azure = azure + ', ' + tag['name']
            return redirect('/login')
    

    return render_template('login.html', username=user['username'], path=UPLOAD_FOLDER, filename=UPLOAD_FILE, azure=azure)

@app.route('/authenticate', methods=['GET', 'POST'])
def authenticate():
    global UPLOAD_FILE
    auth = imageKeyMatch(user['key'])
    if auth:
        return redirect('index')
    else:
        UPLOAD_FILE = None;
        return redirect('upload')


@app.route('/')
def splash():
    return redirect('/upload')

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html', username=user['username'], path=UPLOAD_FOLDER, filename=UPLOAD_FILE, azure=azure)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    global vehicle_global
    info = vehicle_global.info()
    make = info['make']
    model = info['model']
    year = info['year']
    return render_template('dashboard.html', make=make, model=model, year=year)

@app.route('/index', methods=['GET'])
def index():
    global latitude
    global longitude
    return render_template('index.html', latitude=latitude, longitude=longitude)

@app.route('/smartcar_login', methods=['GET'])
def smartcar_login():
    auth_url = client.get_auth_url()
    return redirect(auth_url)

@app.route('/exchange', methods=['GET'])
def exchange():
    code = request.args.get('code')
    global access
    global vehicle_global
    access = client.exchange_code(code)
    vehicle_ids = smartcar.get_vehicle_ids(
        access['access_token'])['vehicles']
    vehicle_global = smartcar.Vehicle(vehicle_ids[0], access['access_token'])
    return redirect('/index')

# @app.route('/vehicle', methods=['GET'])
# def vehicle():
#     info = vehicle_global.info()
#     print(info)
#     return jsonify(info)

@app.route('/unlock', methods=['GET'])
def unlock():
    global latitude
    global longitude
    global vehicle_global
    latitude = vehicle_global.location()['data']['latitude']
    longitude = vehicle_global.location()['data']['longitude']
    if isCloseEnough(lat_car=latitude, lon_car=longitude, lat_u=latitude+0.00005, lon_u=longitude+0.00005, radius=10):
        vehicle_global.unlock()
        print('unlocked!')
    else:
        pass
    return redirect('/index')

@app.route('/lock', methods=['GET'])
def lock():
    global latitude
    global longitude
    global vehicle_global
    latitude = vehicle_global.location()['data']['latitude']
    longitude = vehicle_global.location()['data']['longitude']
    vehicle_global.lock()
    print('locked!')
    return redirect('/index')

@app.route('/locate', methods=['GET', 'POST'])
def locate():
    global latitude
    global longitude
    global vehicle_global
    latitude = vehicle_global.location()['data']['latitude']
    longitude = vehicle_global.location()['data']['longitude']
    return render_template('index.html', latitude=latitude, longitude=longitude)

@app.route("/api/carLocation")
def carLocation():
	location = {'lat': latitude, 'lng': longitude}
	return jsonify(location)

if __name__ == '__main__':
    #app.run(port=8000)
    app.run()
    print(UPLOAD_FOLDER)
    #imageKeyMatch('C:/Simon/0Workspace/Spring 2019/TAMUHack2019/SmartCar/static/img.jpg', 'banana')