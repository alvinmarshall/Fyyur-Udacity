import logging
from logging import Formatter, FileHandler
from typing import List

import babel
import dateutil.parser
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_migrate import Migrate
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy

from forms import *

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
moment = Moment(app)


# ----------------------------------------------------------------------------#
# Models.
# ----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    shows = db.relationship('Show', backref='venue', lazy=True)

    def __repr__(self):
        return f'<Venue {self.id} {self.name} {self.state} {self.address} {self.phone} {self.genres} {self.image_link}>'


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    website = db.Column(db.String(120))
    seeking_description = db.Column(db.String(120))
    shows = db.relationship('Show', backref='artist', lazy=True)

    def __repr__(self):
        return f'<Artist {self.id} {self.name} {self.city} {self.state} {self.phone} {self.genres} {self.image_link}>'


class Show(db.Model):
    __tablename__ = 'shows'

    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)
    start_time = db.Column(db.DateTime, default=datetime.now(), nullable=False)

    def __repr__(self):
        return f'<Show {self.id} {self.artist_id} {self.venue_id} {self.start_time}>'


# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
    date = dateutil.parser.parse(value)
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format, locale='en')


app.jinja_env.filters['datetime'] = format_datetime


# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#

@app.route('/')
def index():
    return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.
    location_data = db.session.query(Venue.city, Venue.state).distinct(Venue.state)
    data = []
    for location in location_data:
        venue_data = []
        venue_data.extend(Venue.query.filter(Venue.state == location.state).all())
        data.append(
            {
                'city': location.city,
                'state': location.state,
                'venues': venue_data
            }
        )
    return render_template('pages/venues.html', areas=data)


@app.route('/venues/search', methods=['POST'])
def search_venues():
    search_term = get_search_term(request.form)
    venue_list = db.session.query(Venue).filter(Venue.name.ilike(f'%{search_term}%')).all()
    count = len(venue_list)
    response = {
        "count": count,
        "data": venue_list
    }
    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


def get_search_term(form):
    return form.get('search_term', '').lower()


@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    data = find_venue_by_id(venue_id)
    set_venue_genres_as_list(data)
    show_list = data.shows
    past_shows = list(filter(lambda show: show.start_time < datetime.now(), show_list))
    upcoming_shows = list(filter(lambda show: show.start_time > datetime.now(), show_list))
    data.past_shows = past_shows
    data.upcoming_shows = upcoming_shows
    data.past_shows_count = len(past_shows)
    data.upcoming_shows_count = len(upcoming_shows)

    set_show_artist(past_shows)
    set_show_artist(upcoming_shows)
    return render_template('pages/show_venue.html', venue=data)


#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    data = request.form
    try:
        venue = get_form_venue(data)
        db.session.add(venue)
        db.session.commit()
        # on successful db insert, flash success
        flash(f"Venue {data['name']} was successfully listed!")
        return render_template('pages/home.html')
    except Exception as e:
        print(e)
        db.session.rollback()
        flash(f"An error occurred. Venue {data['name']} could not be listed.")
    finally:
        db.session.close()


@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    try:
        Venue.query.filter(Venue.id == venue_id).delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        print(e)
        db.session.rollback()
    finally:
        db.session.close()
        return jsonify({'success': False})


#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
    data = Artist.query.all()
    for artist in data:
        set_artist_genres_as_list(artist)
    return render_template('pages/artists.html', artists=data)


@app.route('/artists/search', methods=['POST'])
def search_artists():
    search_term = get_search_term(request.form)
    artist_list = db.session.query(Artist).filter(Artist.name.ilike(f'%{search_term}%')).all()
    count = len(artist_list)
    response = {
        "count": count,
        "data": artist_list
    }
    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the artist page with the given artist_id
    data = find_artist_by_id(artist_id)
    set_artist_genres_as_list(data)
    show_list = data.shows
    past_shows = list(filter(lambda show: show.start_time < datetime.now(), show_list))
    upcoming_shows = list(filter(lambda show: show.start_time > datetime.now(), show_list))
    data.past_shows = past_shows
    data.upcoming_shows = upcoming_shows
    data.past_shows_count = len(past_shows)
    data.upcoming_shows_count = len(upcoming_shows)

    set_show_venue(past_shows)
    set_show_venue(upcoming_shows)
    return render_template('pages/show_artist.html', artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    form = ArtistForm(request.form)
    artist = find_artist_by_id(artist_id)
    set_artist_genres_as_list(artist)
    form.name.data = artist.name
    form.city.data = artist.city
    form.state.data = artist.state
    form.phone.data = artist.phone
    form.genres.data = artist.genres
    form.image_link.data = artist.image_link
    form.facebook_link.data = artist.facebook_link
    form.seeking_venue.data = artist.seeking_venue
    form.website_link.data = artist.website
    form.seeking_description.data = artist.seeking_description
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    data = request.form
    try:
        artist = get_form_artist(data)
        artist.id = artist_id
        db.session.query(Artist) \
            .filter_by(id=artist_id) \
            .update({column: getattr(artist, column) for column in Artist.__table__.columns.keys()})
        db.session.commit()
        # on successful db update, flash success
        flash(f"Artist {request.form['name']} was successfully Updated!")
        return redirect(url_for('show_artist', artist_id=artist_id))
    except Exception as e:
        print(e)
        db.session.rollback()
        flash(f"An error occurred. Artist {request.form['name']} could not be listed.")
    finally:
        db.session.close()


@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    form = VenueForm(request.form)
    venue = find_venue_by_id(venue_id)
    set_artist_genres_as_list(venue)
    form.name.data = venue.name
    form.city.data = venue.city
    form.state.data = venue.state
    form.address.data = venue.address
    form.phone.data = venue.phone
    form.genres.data = venue.genres
    form.image_link.data = venue.image_link
    form.facebook_link.data = venue.facebook_link
    form.seeking_talent.data = venue.seeking_talent
    form.website_link.data = venue.website
    form.seeking_description.data = venue.seeking_description
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    data = request.form
    try:
        venue = get_form_venue(data)
        venue.id = venue_id
        db.session.query(Venue) \
            .filter_by(id=venue_id) \
            .update({column: getattr(venue, column) for column in Venue.__table__.columns.keys()})
        db.session.commit()
        # on successful db update, flash success
        flash(f"Venue {request.form['name']} was successfully Updated!")
        return redirect(url_for('show_artist', artist_id=venue_id))
    except Exception as e:
        print(e)
        db.session.rollback()
        flash(f"An error occurred. Venue {data['name']} could not be listed.")
    finally:
        db.session.close()

    return redirect(url_for('show_venue', venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    data = request.form
    try:
        artist = get_form_artist(data)
        db.session.add(artist)
        db.session.commit()
        # on successful db insert, flash success
        flash(f"Artist {request.form['name']} was successfully listed!")
        return render_template('pages/home.html')
    except Exception as e:
        print(e)
        db.session.rollback()
        flash(f"An error occurred. Artist {request.form['name']} could not be listed.")
    finally:
        db.session.close()


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
    # displays list of shows at /shows
    show_list = Show.query.join(Artist, Artist.id == Show.artist_id).join(Venue, Venue.id == Show.venue_id).all()
    data = []
    for show in show_list:
        data.append({
            "venue_id": show.venue_id,
            "venue_name": show.venue.name,
            "artist_id": show.artist_id,
            "artist_name": show.artist.name,
            "artist_image_link": show.artist.image_link,
            "start_time": str(show.start_time)
        })
    return render_template('pages/shows.html', shows=data)


@app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    try:
        show = get_form_show(request.form)
        db.session.add(show)
        db.session.commit()
        # on successful db insert, flash success
        flash('Show was successfully listed!')
        return render_template('pages/home.html')
    except Exception as e:
        print(e)
        flash('An error occurred. Show could not be added')
        db.session.rollback()
    finally:
        db.session.close()


#  Common functions
#  ----------------------------------------------------------------
def get_form_artist(data) -> Artist:
    return Artist(
        name=data['name'],
        city=data['city'],
        state=data['state'],
        phone=data['phone'],
        genres=','.join(data.getlist('genres')),
        image_link=data['image_link'],
        facebook_link=data['facebook_link'],
        seeking_venue=True if 'seeking_venue' in data else False,
        website=data['website'] if 'website' in data else None,
        seeking_description=data['seeking_description'] if 'seeking_description' in data else None,
    )


def get_form_venue(form) -> Venue:
    return Venue(
        name=form['name'],
        city=form['city'],
        state=form['state'],
        address=form['address'],
        phone=form['phone'],
        genres=','.join(form.getlist('genres')),
        image_link=form['image_link'],
        facebook_link=form['facebook_link'],
        seeking_talent=True if 'seeking_talent' in form else False,
        website=form['website'] if 'website' in form else None,
        seeking_description=form['seeking_description'] if 'seeking_description' in form else None,
    )


def get_form_show(form) -> Show:
    return Show(
        artist_id=form['artist_id'],
        venue_id=form['venue_id'],
        start_time=form['start_time']
    )


def set_artist_genres_as_list(artist: Artist):
    artist.genres = artist.genres.split(',')


def set_venue_genres_as_list(venue: Venue):
    if venue is None:
        return
    venue.genres = venue.genres.split(',')


def set_show_venue(show_list: List[Show]):
    for show in show_list:
        show.venue_image_link = show.venue.image_link
        show.venue_name = show.venue.name
        show.start_time = str(show.start_time)


def set_show_artist(show_list: List[Show]):
    if show_list is None:
        return
    for show in show_list:
        show.artist_id = show.artist.id
        show.artist_name = show.artist.name
        show.artist_image_link = show.artist.image_link
        show.start_time = str(show.start_time)


def find_artist_by_id(artist_id):
    return Artist.query.filter(Artist.id == artist_id).first()


def find_venue_by_id(venue_id):
    return Venue.query.filter(Venue.id == venue_id).first()


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
