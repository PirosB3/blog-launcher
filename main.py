import flask
from flask import Flask
from flask import render_template
from flask import request
from flask import abort

import boto
import boto.ec2
import functools

app = Flask(__name__)

AMAZON_REGION = "us-west-1"
AMAZON_TAG_KEY = "provider"
AMAZON_TAG_VALUE = "daniel-pyrathon"

@app.route('/')
def index():
    return render_template('index.html')

def fetch_amazon_credentials(f):

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        amazon_id = request.headers.get('amazon-id')
        amazon_secret = request.headers.get('amazon-secret')
        if None in [amazon_id, amazon_secret]:
            abort(401)

        kwargs['amazon_id'] = amazon_id
        kwargs['amazon_secret'] = amazon_secret
        return f(*args, **kwargs)

    return wrapper

def get_tagged_instances(connection):
    all_reservations = connection.get_all_instances(
        filters={
            "tag-key": AMAZON_TAG_KEY,
            "tag-value": AMAZON_TAG_VALUE
        }
    )
    results = {}
    for reservation in all_reservations:
        for instance in reservation.instances:
            results[instance.id] = instance
    return results

def make_instance(amazon_id, amazon_secret):
    return boto.ec2.connect_to_region(
        AMAZON_REGION,
        aws_access_key_id=amazon_id,
        aws_secret_access_key=amazon_secret,
    )

@app.route('/api/instances')
@fetch_amazon_credentials
def instances(amazon_id, amazon_secret):

    # Get Amazon instance
    conn = make_instance(amazon_id, amazon_secret)

    # Fetch tagged instances map
    try:
        tagged_instances = get_tagged_instances(conn)
        return flask.jsonify(items=sorted(tagged_instances.keys()))
    except boto.exception.EC2ResponseError, e:
        abort(e.status)

if __name__ == '__main__':
    app.debug = True
    app.run()
