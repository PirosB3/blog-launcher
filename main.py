import flask
from flask import Flask
from flask import render_template
from flask import request
from flask import abort
from flask.json import JSONEncoder

import boto
import boto.ec2
import functools
import os

app = Flask(__name__)

AMAZON_REGION = "us-west-1"
AMAZON_TAG_KEY = "provider"
AMAZON_TAG_VALUE = "daniel-pyrathon"
AMAZON_DEFAULT_SECURITY_GROUP = "daniel-pyrathon"
WORDPRESS_AMI_ID = "ami-d9bb5e9d"


class AmazonInstanceWrapper(object):
    def __init__(self, instance):
        self.instance = instance
        self.state = None

    def set_state(self, state):
        self.state = state


class AWSJSONEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, AmazonInstanceWrapper):
            serialized_instance = {
                'state': obj.instance.state.capitalize(),
                'ip': obj.instance.ip_address
            }
            if obj.state:
                status = obj.state.system_status.status
                serialized_instance['check_status'] = status
            return serialized_instance
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
    running_instances = []
    results = {}
    for reservation in all_reservations:
        for instance in reservation.instances:
            results[instance.id] = AmazonInstanceWrapper(instance)
            if instance.state == u'running':
                running_instances.append(instance.id)

    for instance_status in connection.get_all_instance_status(
            instance_ids=running_instances):
        results[instance_status.id].set_state(instance_status)

    return results


def make_instance(amazon_id, amazon_secret):
    return boto.ec2.connect_to_region(
        AMAZON_REGION,
        aws_access_key_id=amazon_id,
        aws_secret_access_key=amazon_secret,
    )


def get_security_group(connection):
    try:
        return connection.get_all_security_groups(
            groupnames=[AMAZON_DEFAULT_SECURITY_GROUP]
        )[0]
    except boto.exception.EC2ResponseError:
        sg = connection.create_security_group(AMAZON_DEFAULT_SECURITY_GROUP,
                                              'Wordpress security group')
        sg.authorize('tcp', 80, 80, '0.0.0.0/0')
        return sg


@app.route('/api/instances/<instance_id>', methods=['DELETE'])
@fetch_amazon_credentials
@fetch_connection_and_instances
def stop_instance(instance_id, connection, instances, amazon_id,
                  amazon_secret):
    try:
        selected_instance = instances[instance_id].instance
    except KeyError:
        abort(404)

    # Terminate instance
    selected_instance.stop()
    return "", 202


@app.route('/api/instances/<instance_id>', methods=['UPDATE'])
@fetch_amazon_credentials
@fetch_connection_and_instances
def update_instance(instance_id, connection, instances, amazon_id,
                    amazon_secret):
    try:
        selected_instance = instances[instance_id].instance
    except KeyError:
        abort(404)

    # Start instance
    selected_instance.start()
    return "", 202


@app.route('/api/instances', methods=["CREATE"])
@fetch_amazon_credentials
def create_instances(amazon_id, amazon_secret):

    # Get Amazon instance
    connection = make_instance(amazon_id, amazon_secret)
    sg = get_security_group(connection)

    res = connection.run_instances(
        WORDPRESS_AMI_ID,
        instance_type='t1.micro',
        security_groups=[sg])

    res.instances[0].add_tag(AMAZON_TAG_KEY, AMAZON_TAG_VALUE)
    return "", 202


@app.route('/api/instances')
@fetch_amazon_credentials
@fetch_connection_and_instances
def instances(connection, instances, amazon_id, amazon_secret):
    # Map each instance object to it's state
    return flask.jsonify(instances)


if __name__ == '__main__':
    app.debug = bool(os.environ.get('BITNAMI_DEBUG', False))
    app.json_encoder = AWSJSONEncoder
    app.run()
