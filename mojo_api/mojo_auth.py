import mechanize
import cookielib
import logging
import getpass

def mojo_auth(username, password, 
    useragent="Mozilla/5.0 (X11; Linux x86_64; rv:34.0) Gecko/20100101 Firefox/34.0",
    debug=False):

    jive_instance="https://mojo.redhat.com"
    # Browser
    br = mechanize.Browser()
    # Add user agent
    br.addheaders = [('User-agent', useragent)]

    # Cookie Jar
    cj = cookielib.CookieJar()
    br.set_cookiejar(cj)

    # Browser options
    br.set_handle_equiv(True)
    br.set_handle_redirect(True)
    br.set_handle_referer(True)
    br.set_handle_robots(False)

    # Follows refresh 0 but not hangs on refresh > 0
    br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    #Want debugging messages?
    if debug:
        br.set_debug_http(True)
        br.set_debug_redirects(True)
        br.set_debug_responses(True)
    
    ##########################
    # SALMRequest token Page #
    ##########################
    try:
        # Open mojo login page to get SAMLRequest token
        br.open(jive_instance)
        # I expect there's only 1 form, select it
        br.select_form(nr=0)
        # click form submit, there's hidden SAMLRequest variable
        br.submit() 
        # after submit browser is taken to https://saml.redhat.com/idp/
    except:
        logging.error("error in SALMRequest token Page 1")
        #raise

    ##############
    # Login page #
    ##############
    try:
        # on https://saml.redhat.com/idp/ (Red Hat Internal SSO)
        # select form <form id="login_form" name="login_form" method="post" action="j_security_check" enctype="application/x-www-form-urlencoded">...</form>
        br.select_form(predicate=lambda f: 'action' in f.attrs and f.attrs['action'] == 'j_security_check')
        # fill in the form
        br.form['j_username'] = username
        br.form['j_password'] = password
        # click form submit
        br.submit() 
        # after successful submit browser is taken to https://saml.redhat.com/idp/
    except:
        logging.error("error in Login page")
        raise

    ###########################
    # SALMResponse token Page #
    ###########################
    if 'login_form' in [form.name for form in br.forms()]:
        logging.error("Please check your username/password and try again")
    else:
        try:
            # select form <FORM METHOD="POST" ACTION="https://mojo.redhat.com/saml/sso">...</FORM>
            br.select_form(predicate=lambda f: 'action' in f.attrs and 'saml' in f.attrs['action'])
            # click form submit, there's hidden SAMLResponse variable
            br.submit()
            # after this browser is taken to mojo home
        except:
            logging.error("error in SALMRequest token Page 2")
            raise

    #######################################################
    # do a dummy call to api, this will get X-JCAPI-Token #
    #######################################################
    if 'X-JIVE-USER-ID' in br.response().info():
        try:
            br.open('''%s/api/core/v3/people/%s''' % (jive_instance, br.response().info()['X-JIVE-USER-ID']))
        except:
            logging.error("error in do a dummy call to api")
            raise
    else:
        logging.error("Expected X-JIVE-USER-ID in response headers to run user lookup and setting of X-JCAPI-Token")
        raise

    # Finished
    return br, cj


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    # Setup user/password
    username = raw_input("Username [%s]: " % getpass.getuser())
    if not username:
        username = getpass.getuser()
    password = getpass.getpass()
    # Run mojo
    logging.info("Please wait, running as %s" % username)
    # mojo = 'https://mojo.redhat.com'
    br, cj =  mojo_auth(username, password, debug=True)
    if 'X-JIVE-USER-ID' in br.response().info():
        print br.response().info()['X-JIVE-USER-ID']
    for cookie in cj:
        print cookie.name, cookie.value
    