from datetime import datetime
from flask_login import current_user


def audit_log(*args):
    with open('audit.log', 'a') as fd:
        prefix = '{:%Y-%m-%d %H:%M:%S}: {} has '.format(
            datetime.now(), current_user.username)
        fd.write(prefix)
        fd.write(' '.join(args))
        fd.write('\n')
