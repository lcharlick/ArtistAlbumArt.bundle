import os
import re
import hashlib
import unicodedata
import mutagen

# Settings lifted from localmedia agent
IMAGE_EXTS = ['jpg', 'png', 'jpeg', 'tbn']
ART_EXTS = ['jpg', 'jpeg', 'png', 'tbn']
POSTER_FILES = ['poster', 'default', 'cover', 'movie', 'folder']


# Unicode control characters can appear in ID3v2 tags but are not legal in XML.
RE_UNICODE_CONTROL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                     u'|' + \
                     u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                     (
                         unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                         unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                         unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff)
                     )


def unicodize(s):
    filename = s
    try:
        filename = unicodedata.normalize('NFC', unicode(s.decode('utf-8')))
    except:
        Log('Failed to unicodize: ' + filename)
    try:
        filename = re.sub(RE_UNICODE_CONTROL, '', filename)
    except:
        Log('Couldn\'t strip control characters: ' + filename)
    return filename


#####################################################################################################################

# Suppress critical log entry
def Start():
    pass


def get_album_art(media, metadata):
    # valid_posters = []
    path = None
    for track in media.tracks:
        for item in media.tracks[track].items:
            for part in item.parts:
                filename = unicodize(part.file)
                path = os.path.dirname(filename)
                (file_root, fext) = os.path.splitext(filename)

                path_files = {}
                for p in os.listdir(path):
                    path_files[p.lower()] = p

                # Look for posters
                poster_files = POSTER_FILES + [os.path.basename(file_root), os.path.split(path)[-1]]
                for ext in ART_EXTS:
                    for name in poster_files:
                        file = (name + '.' + ext).lower()
                        if file in path_files.keys():
                            data = Core.storage.load(os.path.join(path, path_files[file]))
                            poster_name = hashlib.md5(data).hexdigest()
                            # valid_posters.append(poster_name)

                            if poster_name not in metadata.posters:
                                metadata.posters[poster_name] = Proxy.Media(data)
                                Log('Local asset image added (poster): ' + file + ', for file: ' + filename)
                            else:
                                Log('Skipping local poster since its already added')

                Log('Reading ID3 tags from: ' + filename)
                try:
                    tags = mutagen.File(filename)
                    Log('Found tags: ' + str(tags.keys()))
                except:
                    Log('An error occurred while attempting to read ID3 tags from ' + filename)
                    return

                try:
                    valid_posters = []
                    frames = [f for f in tags if f.startswith('APIC:')]
                    for frame in frames:
                        if (tags[frame].mime == 'image/jpeg') or (tags[frame].mime == 'image/jpg'):
                            ext = 'jpg'
                        elif tags[frame].mime == 'image/png':
                            ext = 'png'
                        elif tags[frame].mime == 'image/gif':
                            ext = 'gif'
                        else:
                            ext = ''
                        poster_name = hashlib.md5(tags[frame].data).hexdigest()
                        valid_posters.append(poster_name)
                        if poster_name not in metadata.posters:
                            Log('Adding embedded APIC art: ' + poster_name)
                            metadata.posters[poster_name] = Proxy.Media(tags[frame].data, ext=ext)
                except Exception, e:
                    Log('Exception adding posters: ' + str(e))


class ArtistAlbumArt(Agent.Artist):
    name = 'Artist Album Art'
    languages = [Locale.Language.NoLanguage]
    primary_provider = False
    persist_stored_files = False
    contributes_to = ['com.plexapp.agents.discogs', 'com.plexapp.agents.lastfm', 'com.plexapp.agents.plexmusic',
                      'com.plexapp.agents.none']

    def search(self, results, media, lang):
        results.Append(MetadataSearchResult(id='null', name=media.artist, score=100))

    def update(self, metadata, media, lang):
        for album in media.children:
            get_album_art(album, metadata)
