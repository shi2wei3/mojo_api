from mojo_api import MOJOApi
import argparse
import logging
import json


def make_call(mojo, url, json_data, method):
    if json_data:
        if method == 'post':
            return mojo.post(url, json.dumps(json_data))
        if method == 'put':
            return mojo.put(url, json.dumps(json_data))
    else:
        if method == 'delete':
            return mojo.delete(url)
        if method == 'get':
            return mojo.get(url)


def load_json_data(json_file):
    if json_file:
        try:
            with open(json_file) as f:
                data = f.read()
        except:
            logging.error("Unable to open %s" % json_file)
            raise
        try:
            json_data = json.loads(data)
            return json_data
        except:
            logging.error("Unable to convert contents of %s to json" % data)
            raise


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", type=str, dest='url',
                        help="mojo api url", required=True)
    parser.add_argument("-j", type=str, dest='json',
                        help="optional json data file to be posted to api url", required=False)
    parser.add_argument("-m", type=str, dest='method', choices=['get', 'post', 'put', 'delete'], default='get',
                        help="put or post http  method to use when posting json file, default post", required=False)
    parser.add_argument("-o", type=str, dest='output',
                        help="output file to write reponse from mojo", required=False)
    parser.add_argument("-v", action="store_true", dest='debug',
                        help="enable debug messages", required=False)

    args = parser.parse_args()
    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
        logging.debug("Running in debug mode")
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    # convert data file to json
    json_data = load_json_data(args.json)
    # setup mojo
    mojo = MOJOApi()
    # make api call
    json_result = make_call(mojo, args.url, json_data, args.method)
    # save output if output specified
    if args.output:
        with open(args.output, 'w') as outfile:
            json.dump(json_result, outfile, sort_keys=True, indent=4)
        logging.info("Output saved to %s" % args.output)
    else:
        logging.info("Result:\n%s" % json.dumps(json_result, sort_keys=True, indent=4))


if __name__ == "__main__":
    main()
