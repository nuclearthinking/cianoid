import datetime
import logging
from logging import DEBUG

import jinja2
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from peewee import SqliteDatabase, Model, PrimaryKeyField, CharField, IntegerField, DateTimeField
from tornado import httpclient, ioloop
from tornado import web
from tornado.options import define, options
from tornado.web import RequestHandler
from tornado_jinja2 import Jinja2Loader

import settings

db = SqliteDatabase('cianoid.db')
define("port", default=8888, help="run on the given port", type=int)
jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(settings.TEMPLATE_PATH), autoescape=False)
jinja2_env.globals['STATIC_PREFIX'] = '/'
jinja2_loader = Jinja2Loader(jinja2_env)
options.parse_command_line()


class Counter(Model):
    id = PrimaryKeyField()
    name = CharField(unique=True, null=False)
    counter = IntegerField(null=True)

    class Meta:
        database = db


class History(Model):
    id = PrimaryKeyField()
    score = IntegerField()
    date = DateTimeField()

    class Meta:
        database = db


def check_cian():
    try:
        response = httpclient.HTTPClient().fetch('https://www.cian.ru/')
    except httpclient.HTTPError as e:
        if e.response.code >= 400:
            erase_counter()
    except Exception as e:
        logging.getLogger(__name__).exception('Something goes wrong')


def increment_counter():
    if Counter.select().where(Counter.id == 1).first(1):
        counter = Counter.select().where(Counter.id == 1).peek(1)
        counter.counter = counter.counter + 1
        counter.save()
    else:
        Counter(name='days_without_downtime', counter=1).save()


def erase_counter():
    if is_counter_exist():
        counter = Counter.select().where(Counter.id == 1).peek(1)
        if counter.counter != 0:
            History.create(score=counter.counter, date=datetime.datetime.now())
        counter.counter = 0
        counter.save()


class AloneHandler(RequestHandler):
    def get(self, *args, **kwargs):
        days_count = ...
        if is_counter_exist():
            counter = Counter.select().where(Counter.id == 1).first(1)
            days_count = counter.counter
        else:
            days_count = 0
        days_str = '0' * (4 - len(str(days_count))) + str(days_count)
        q, w, e, r = days_str
        top10 = None
        if History.select().exists():
            top10 = History.select().order_by(History.score.desc()).first(8)
            for item in top10:
                date = item.date
                item.date = date.strftime('%d %B %Y %H:%M')
        self.render('count.html', one=q, two=w, three=e, four=r, top10=top10)


def is_counter_exist():
    if Counter.select().where(Counter.id == 1).first(1):
        return True
    else:
        return False


def main():
    db.create_tables([Counter, History], safe=True)
    logging.basicConfig(level=DEBUG)
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=increment_counter,
        trigger=CronTrigger(
            start_date=datetime.datetime.now(),
            second='0',
            minute='0',
        ),
        max_instances=1
    )
    scheduler.add_job(
        func=check_cian,
        trigger=IntervalTrigger(minutes=1, start_date=datetime.datetime.now())
    )
    scheduler.start()
    cfg = {
        'template_loader': jinja2_loader,
        "static_path": settings.STATIC_PATH,
    }
    app = web.Application([
        web.url(r'/', AloneHandler)
    ], **cfg)
    app.listen(options.port)
    ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
