import flask
from flask import Flask
from flask import render_template
from flask import request
from flask import abort
from flask.json import JSONEncoder

import boto
import boto.ec2
import functools

app = Flask(__name__)

AMAZON_REGION = "us-west-1"
AMAZON_TAG_KEY = "provider"
AMAZON_TAG_VALUE = "daniel-pyrathon"


class AWSJSONEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, boto.ec2.instance.Instance):
            return obj.state.capitalize()
        return JSONEncoder.default(self, obj)


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

def fetch_connection_and_instances(f):

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        amazon_id = kwargs['amazon_id']
        amazon_secret = kwargs['amazon_secret']

        # Get Amazon instance
        kwargs['connection'] = make_instance(amazon_id, amazon_secret)

        # Fetch tagged instances map
        try:
            kwargs['instances'] = get_tagged_instances(kwargs['connection'])
        except boto.exception.EC2ResponseError, e:
            abort(e.status)

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

@app.route('/api/instances/<instance_id>', methods=['DELETE'])
@fetch_amazon_credentials
@fetch_connection_and_instances
def stop_instance(instance_id, connection, instances, amazon_id, amazon_secret):

    try:
        selected_instance = instances[instance_id]
    except KeyError:
        abort(404)

    # Terminate instance
    selected_instance.terminate()
    return "", 202


@app.route('/api/instances')
@fetch_amazon_credentials
@fetch_connection_and_instances
def instances(connection, instances, amazon_id, amazon_secret):
    # Map each instance object to it's state
    return flask.jsonify(instances)

if __name__ == '__main__':
    app.debug = True
    app.json_encoder = AWSJSONEncoder
    app.run()
