from mojo_api import MOJOApi, Report
import argparse
import getpass
import logging
import json
import os


def main():
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", type=str, dest='filter_method', choices=['subject', 'from', 'body'],
                        help="Filter method for Emails", required=False)
    parser.add_argument("-k", type=str, dest='filter_key',
                        help="Filter keywords for Emails", required=False)
    parser.add_argument("-r", type=str, dest='report_id',
                        help="Report document id", required=False)
    parser.add_argument("-t", type=str, dest='title',
                        help="Report title", required=False)
    parser.add_argument("-m", type=int, dest='months',
                        help="Count of months to check for Emails", required=False)
    parser.add_argument("-e", action="store_true", dest='delete',
                        help="Delete all mojo pages in the report document id", required=False)
    parser.add_argument("-u", type=str, dest='username',
                        help="kerberos username, will be prompted if not specified", required=False)
    parser.add_argument("-p", type=str, dest='password',
                        help="kerberos password, will be prompted if not specified", required=False)
    parser.add_argument("-x", action="store_true", dest='dry_run',
                        help="enable dry-run mode", required=False)
    parser.add_argument("-d", action="store_true", dest='debug',
                        help="enable debug messages", required=False)


    args = parser.parse_args()
    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
        logging.debug("Running in debug mode")
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
        logging.info("Running in normal mode")
    # load config file
    config = {}
    try:
        with open(os.path.expanduser('~') + '/.mojo_report.cfg', 'r') as f:
            config = json.load(f)
    except IOError, e:
        if e.errno == 2:
            logging.debug("Config file /.mojo_report.cfg not founded.")

    # get username/password
    if args.username:
        username = args.username
    elif config.get('kerberos_username'):
        username = config['kerberos_username']
    else:
        username = raw_input("Username [%s]: " % getpass.getuser())
        if not username:
            username = getpass.getuser()
    if args.password:
        password = args.password
    elif config.get('kerberos_password'):
        password = config['kerberos_password']
    else:
        password = getpass.getpass('Please enter your kerberos password:')
    # get report_id or report title
    if args.report_id:
        try:
            report_id = int(args.report_id)
        except ValueError:
            print "Report DOC-ID is not Integer: %s" % args.report_id
            args.report_id = None
            report_id = 0
    elif config.get('report_id'):
        try:
            report_id = int(config['report_id'])
        except ValueError:
            print "Report DOC-ID is not Integer: %s" % config['report_id']
            args.report_id = None
            report_id = 0
    else:
        report_id = 0
    if args.title:
        title = args.title
    elif config.get('title'):
        title = config['title']
    else:
        title = ''
    if (not args.report_id and not args.title) and (not config.get('report_id') and not config.get('title')):
        str_report_id = raw_input("Existing report DOC-ID / New report titile: ")
        try:
            report_id = int(str_report_id)
            print "Existing report DOC-ID %d" % report_id
        except ValueError:
            title = str_report_id
            print "New report titile: %s" % title
    if report_id != 0 and title != '':
        logging.info('Both report_id and title are given, will use report_id and omit title')
    # months
    if args.months:
        try:
            months = int(args.months)
        except ValueError:
            print "Months is not Integer: %s" % args.months
            months = None
    elif config.get('months'):
        try:
            months = int(config['months'])
        except ValueError:
            print "Months is not Integer: %s" % config['months']
            months = None
    else:
        months = None
    # filter
    if args.filter_method:
        filter_method = args.filter_method
    elif config.get('filter_method'):
        filter_method = config['filter_method']
    else:
        filter_method = None
    if args.filter_key:
        filter_key = args.filter_key
    elif config.get('filter_key'):
        filter_key = config['filter_key']
    else:
        filter_key = None
    # place_id
    if config.get('place_id'):
        place_id = config['place_id']
    else:
        place_id = None
    # mail_list
    if config.get("mail_list"):
        mail_list = config['mail_list']
    else:
        mail_list = None

    mojo = MOJOApi(username, password)

    report = Report(mojo, months=months, place_id=place_id, title=title, mail_list=mail_list, filter_method=filter_method, filter_key=filter_key)
    if args.delete:
        if report_id != 0:
            print report_id
            report.delete_report(report_id)
            return 0
        else:
            print "-e given but not assign report id"
            return 1

    if report_id != 0:
        report.load_report(report_id)
        report.publish_report(report_id, dry_run=args.dry_run)
    else:
        report.publish_report(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
