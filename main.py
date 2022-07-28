#!/usr/bin/env python
"""
MP3 Music Player [CLI]
Created By Arijit Bhowmick [sys41x4]

[
    Created For : Internship Project,
    Internship Provider : UNIcompiler
]
"""
from asyncio import Future, ensure_future
import os, glob
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
from pygame import mixer
from tinytag import TinyTag
import json, yaml

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.lexers import DynamicLexer, PygmentsLexer
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import (
    Button,
    Dialog,
    Label,
    MenuContainer,
    MenuItem,
    SearchToolbar,
    TextArea,
)

mixer.init()



class ApplicationState:
    """
    Application state.

    For the simplicity, we store this as a global, but better would be to
    instantiate this as an object and pass at around.
    """

    show_status_bar = True
    current_path = None





class Handlers:
    def __init__(self):

        self.search_toolbar = SearchToolbar()
        self.header_text = "MP3 Music Player [Arijit Bhowmick [sys41x4]]"
        self.get_statusbar_text = " Press Ctrl+C to open menu. "

        self.music_detail = TextArea(
            scrollbar=True,
            line_numbers=True,
        )

        self.music_metaData = TextArea(
            scrollbar=True,
            line_numbers=True,
        )

        self.text_field = TextArea(
            lexer=DynamicLexer(
                lambda: PygmentsLexer.from_filename(
                    ApplicationState.current_path or ".mp3", sync_from_start=False
                )
            ),
            scrollbar=True,
            line_numbers=True,
            search_field=self.search_toolbar,
        )

        self.status = Window(
            FormattedTextControl('IDLE'), style="class:status",
            align=WindowAlign.CENTER,
        )

        self.play_pause = Window(
            FormattedTextControl(text='|>'),
            align=WindowAlign.CENTER,
            style="bg:purple fg:white",
            
        )

        self.full_meta_data = Window(
            FormattedTextControl(text='META-DATA'),
            style="bg:black fg:white",
            align=WindowAlign.LEFT,
        )

        self.volume = Window(
            FormattedTextControl(text=''),
            style="bg:black fg:blue",
            align=WindowAlign.CENTER,
        )

        self.current_song_time = Window(
            FormattedTextControl(text='0:0'),
            style="bg:black fg:green",
            align=WindowAlign.LEFT,
        )

        self.total_song_time = Window(
            FormattedTextControl(text='0:0'),
            style="bg:black fg:red",
            align=WindowAlign.RIGHT,
        )

        self.song_progress = Window(
            FormattedTextControl(text='0%'),
            style="bg:black fg:purple",
            align=WindowAlign.CENTER,
        )

    def exitApp(self):
        music_controls.exit()
        get_app().exit()

    def help(self):
        self.show_message("Help", """
[Important Controls]

Ctrl+C : Interact with Menu Items
F6 : Exit Application
h : Show Help Details
a : Show About

[File/Directory Controls]

o : Open .mp3 Media File
f : Open .mp3 Song Directory/Folder

[Song Controls]

<space> : Play/Pause Song
p : Previous Song
n : Next Song
u : Get Current Song Progress
. : Stop Currently Loaded Song
d : Song Details


[Volume Controls]

+ : Volume Up
- : Volume Down

Other Help Details at : https://sys41x4.github.io
""")



    def get_statusbar_right_text(self):
        return " {}:{}  ".format(
            self.text_field.document.cursor_position_row + 1,
            self.text_field.document.cursor_position_col + 1,
        )

    def show_message(self, title, text):
        async def coroutine():
            dialog = MessageDialog(title, text)
            await self.show_dialog_as_float(dialog)

        ensure_future(coroutine())


    async def show_dialog_as_float(self, dialog):
        "Coroutine."
        global root_container
        float_ = Float(content=dialog)
        root_container.floats.insert(0, float_)

        app = get_app()

        focused_before = app.layout.current_window
        app.layout.focus(dialog)
        result = await dialog.future
        app.layout.focus(focused_before)

        if float_ in root_container.floats:
            root_container.floats.remove(float_)

        return result

    def showMetaDataBox(self):
        '''
        load metadata to Box
        '''

        self.show_message(self.header_text, 'META-DATA\n\n'+music_controls.song_meta_data_yaml)



    def loadMusic(self):
        '''
        Open MP3 Music to play
        '''
        async def coroutine():
            open_dialog = TextInputDialog(
                title=self.header_text,
                label_text="Enter MP3 Music File Path:",
                completer=PathCompleter(),
            )

            path = await self.show_dialog_as_float(open_dialog)
            ApplicationState.current_path = path

            if path is not None:
                try:
                    music_controls.loadSongPaths(os.path.join(path), 'file')
                except OSError as e:
                    self.show_message("Error", f"{e}")

        ensure_future(coroutine())
    



handler = Handlers()


class MusicControls:

    def __init__(self):
        self.song_list = []
        self.song_meta_data = {}
        self.song_min_meta_data = {}
        self.song_meta_data_yaml = ''
        self.song_min_meta_data_yaml = ''
        self.status = 'IDLE'
        mixer.music.set_volume(1) # Set to full Volume 100%
        self.volume = int(mixer.music.get_volume()*100)
        self.max_volume = 100
        self.min_volume = 0
        self.volume_change_frequency = 10
        self.current_song_index = None
        self.song_directory_path = ''

    def loadSong(self):
        '''
        load Song to Play
        '''
        if (self.current_song_index != None) and (len(self.song_list)>0):
            mixer.music.unload() # Unload the file to save system resource
            
            
            mixer.music.load(os.path.join(self.song_directory_path, self.song_list[self.current_song_index]), namehint="mp3") # Load the file

            self.volume = int(mixer.music.get_volume()*100)

            

            # Meta Data Loading
            self.song_min_meta_data = {}
            self.fetchSongDetails(os.path.join(self.song_directory_path, self.song_list[self.current_song_index]))
            self.minMetaData()

            
            handler.total_song_time.content.text = str(int(self.song_meta_data['duration']))
            self.status = handler.status.content.text = 'playing'
            handler.play_pause.content.text = '||'
            handler.music_detail.text = self.song_min_meta_data_yaml+f'File Location: {self.song_directory_path}\nFile Name: {self.song_list[self.current_song_index]}'
            handler.full_meta_data.content.text = self.song_meta_data_yaml

        elif (self.current_song_index == None) and (len(self.song_list)==0):
            handler.show_message("Error", "Songs are not Loaded Yet")

    def loadSongPaths(self, path, type):
        '''
        Load all Songs From Particular Directory
        '''


        if type == 'dir':
            if os.path.isdir(path)==True:
                self.song_directory_path = os.path.join(path)
                self.song_list = []
                song_list = glob.glob(os.path.join(path, '*.mp3'))

                if len(song_list) == 0:
                    handler.show_message("Suggession", "Directory does'nt contain any supported (MP3) media file")
                else:
                    for file_path in song_list:
                        self.song_list+=[os.path.split(file_path)[-1]]

                    handler.text_field.text = '\n'.join(self.song_list)
                    self.current_song_index = 0

            elif os.path.isdir(path)==False:
        
                handler.show_message("Error", "Invalid Directory Path")

        elif type=='file':
            if os.path.isfile(path)==True:
                if path.endswith('.mp3'):
                    self.song_directory_path = os.path.split(path)[0]
                    self.song_list = [os.path.split(path)[-1]]

                    handler.text_field.text = self.song_list[0]
                    self.current_song_index = 0

                else:
                    handler.show_message("Error", "Not a supported MP3 File")
                    
            elif os.path.isfile(path)==False:
                handler.show_message("Error", "Invalid MP3 File Path")

        

    def playSong(self):
        '''
        Play Current mp3 song
        '''
        if self.current_song_index!=None:
            mixer.music.play()
            self.status = 'playing'
    
    def pauseSong(self):
        '''
        Pause Currently Playing Song
        '''
        if self.current_song_index!=None:
            mixer.music.pause()
            self.status = 'paused'
    
    def unpauseSong(self):
        '''
        Unpause currently paused Song
        '''
        if self.current_song_index!=None:
            mixer.music.unpause()
            self.status = 'playing'

    def stopSong(self):
        '''
        Stop Currently Playing Song
        '''
        mixer.music.unload()
        mixer.music.stop()
        self.status = 'IDLE'

    def exit(self):
        '''
        Exit
        '''
        self.stopSong()
        mixer.quit()

    def nextSong(self):
        '''
        Play Next song from the song list
        '''
        if self.current_song_index!=None:
            if len(self.song_list)==1:
                self.current_song_index = 0
                self.loadSong()
                self.playSong()

            elif len(self.song_list)>1:
                if (len(self.song_list)>1) and (self.current_song_index+1<len(self.song_list)):
                    self.current_song_index+=1

                else:
                    self.current_song_index=0
                self.loadSong()
                self.playSong()
        elif self.current_song_index==None:
            handler.show_message("Error", "Songs are not Loaded Yet")

    def previousSong(self):
        '''
        Play Previous Song from the Song List
        '''

        if self.current_song_index!=None:
            if len(self.song_list)==1:
                self.current_song_index = 0
                self.loadSong()
                self.playSong()

            elif len(self.song_list)>1:
                if len(self.song_list)==1:
                    pass
                elif (len(self.song_list)>1) and (self.current_song_index==0):
                    self.current_song_index=len(self.song_list)-1
                else:
                    self.current_song_index-=1
                self.loadSong()
                self.playSong()
        elif self.current_song_index==None:
            handler.show_message("Error", "Songs are not Loaded Yet")

    def volumeChange(self, type):
        '''
        Change Volume
        '''
        if (type == 'increase') and (self.volume<self.max_volume):
            self.volume+=self.volume_change_frequency
            mixer.music.set_volume(self.volume*0.01)

        elif (type == 'decrease') and (self.volume>self.min_volume):
            self.volume-=self.volume_change_frequency
            mixer.music.set_volume(self.volume*0.01)

    def currentSongTime(self):
        '''
        Get Current Song Time
        '''

        if self.current_song_index==None:
            return '0:0'

        if (self.status=='playing') or (self.status=='paused'):
            return int(mixer.music.get_pos()*0.001)
        elif (self.status=='idle') or (self.status=='stopped'):
            return 0
        

    def fetchSongDetails(self, file_path):
        '''
        Get Meta Data Details of the MP3 Song
        '''
        self.song_meta_data = json.loads(str(TinyTag.get(file_path)))
        self.song_meta_data_yaml = yaml.dump(self.song_meta_data)

    def minMetaData(self):
        min_meta_data = {
            "Title":"title",
            "Album":"album",
            "Album Artist":"albumartist",
            "Composer":"composer",
        }


        for key in min_meta_data:
            if min_meta_data[key] in self.song_meta_data:
                self.song_min_meta_data.update({key:self.song_meta_data[min_meta_data[key]]})
            else:
                self.song_min_meta_data.update({key:" "})

        self.song_min_meta_data_yaml = yaml.dump(self.song_min_meta_data)



class TextInputDialog:
    def __init__(self, title="", label_text="", completer=None):
        self.future = Future()

        def accept_text(buf):
            get_app().layout.focus(ok_button)
            buf.complete_state = None
            return True

        def accept():
            self.future.set_result(self.text_area.text)

        def cancel():
            self.future.set_result(None)

        self.text_area = TextArea(
            completer=completer,
            multiline=False,
            width=D(preferred=40),
            accept_handler=accept_text,
        )

        ok_button = Button(text="OK", handler=accept)
        cancel_button = Button(text="Cancel", handler=cancel)

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=label_text), self.text_area]),
            buttons=[ok_button, cancel_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog


class MessageDialog:
    def __init__(self, title, text):
        self.future = Future()

        def set_done():
            self.future.set_result(None)

        ok_button = Button(text="OK", handler=(lambda: set_done()))

        self.dialog = Dialog(
            title=title,
            body=HSplit([Label(text=text)]),
            buttons=[ok_button],
            width=D(preferred=80),
            modal=True,
        )

    def __pt_container__(self):
        return self.dialog

def create_title(text: str, dont_extend_width: bool = False) -> Label:
    return Label(text, style="fg:ansiblue", dont_extend_width=dont_extend_width)


# Interact With MusicControl Class and Functions
music_controls = MusicControls()


body = HSplit(
    [
        Window(
            FormattedTextControl("MP3 Music Player [By Arijit Bhowmick [sys41x4]]"),
            style="bg:green fg:white",
            align=WindowAlign.CENTER,
            height=1,
            
        ),
        VSplit(
            [
                HSplit(
                    [
                        Window(
                            FormattedTextControl("Song List"),
                            style="bg:purple fg:white",
                            align=WindowAlign.CENTER,
                            height=1,
                        ),
                        handler.text_field
                    ]
                ),
                
                
                HSplit(
                    [   
                        HSplit(
                            [
                                
                                Window(
                                    FormattedTextControl('Music Dashboard'),
                                    style="bg:blue fg:white",
                                    align=WindowAlign.CENTER,
                                    height=1,
                                    
                                ),

                                handler.music_detail,

                                VSplit(
                                    [
                                        handler.current_song_time,
                                        handler.song_progress,
                                        handler.total_song_time,
                                    ],
                                    height=1,
                                    
                                ),

                                VSplit(
                                    [
                                        Window(
                                            FormattedTextControl('<<'),
                                            align=WindowAlign.CENTER,
                                            style="bg:red fg:black",

                                        ),
                                        handler.play_pause,
                                        Window(
                                            FormattedTextControl('>>'),
                                            align=WindowAlign.CENTER,
                                            style="bg:green fg:black",
                                        ),

                                        
                                    ],
                                    height=1,
                                    
                                ),
                                VSplit(
                                    [
                                        HSplit(
                                            [
                                                Window(
                                                    FormattedTextControl('META-DATA'),
                                                    align=WindowAlign.CENTER,
                                                    style="bg:black fg:blue",
                                                    height=1,
                                                ),
                                                handler.full_meta_data,
                                            ]
                                        ),

                                        HSplit(
                                            [   
                                                Window(
                                                    FormattedTextControl('Other Controls'),
                                                    align=WindowAlign.CENTER,
                                                    style="bg:black fg:blue",
                                                    height=1,
                                                ),
                                                VSplit(
                                                    [
                                                        Window(
                                                            FormattedTextControl('Volume : '),
                                                            align=WindowAlign.CENTER,
                                                            style="bg:black fg:purple",
                                                        ),
                                                        handler.volume,
                                                    ],
                                                ),
                                            ]
                                        ),

                                    ]
                                ),
                            ]
                        ),
                    ]
                ),
                
                 
            ]
        ),
        
        ConditionalContainer(
            content=VSplit(
                [
                    Window(
                        FormattedTextControl(handler.get_statusbar_text), style="class:status"
                    ),
                    handler.status,
                    Window(
                        FormattedTextControl(handler.get_statusbar_right_text),
                        style="class:status.right",
                        width=9,
                        align=WindowAlign.RIGHT,
                    ),
                ],
                height=1,
            ),
            filter=Condition(lambda: ApplicationState.show_status_bar),
        ),
        Window(
            FormattedTextControl(''),
            align=WindowAlign.CENTER,
            style="bg:black fg:black",
            height=1,
        ),
        
    ]
)

# For Testing
handler.music_detail.text = ''

# Startup Assigned Values
handler.volume.content.text = str(music_controls.volume)



# Global key bindings.
bindings = KeyBindings()

# Functional Keys

@bindings.add("f6")
def _exit(event):
    "Exit Application"
    music_controls.stopSong()
    # event.app.exit()
    handler.exitApp()


@bindings.add("u")
def _updateStaticValues(event):
    "Update Static Values"
    handler.current_song_time.content.text = str(music_controls.currentSongTime())
    handler.volume.content.text = str(music_controls.volume)

    if handler.current_song_time.content.text!='0':
        handler.song_progress.content.text = str(int((music_controls.currentSongTime()*100)/int(music_controls.song_meta_data['duration'])))+' %'


@bindings.add("+")
def _volumeUp(event):
    "Increase Volume"
    music_controls.volumeChange('increase')
    handler.volume.content.text = str(music_controls.volume)


@bindings.add("-")
def _volumeDown(event):
    "Decrease Volume"
    music_controls.volumeChange('decrease')
    handler.volume.content.text = str(music_controls.volume)



@bindings.add("c-c")
def _(event):
    "Focus menu."
    event.app.layout.focus(root_container.window)

@bindings.add("a")
def _about(event):
    "Show About Details"
    music_player_controls.about()

@bindings.add("h")
def _help(event):
    "Show Help Details"
    handler.help()

@bindings.add("d")
def _metaDataBox(event):
    "Show Song Meta Data Details"
    handler.showMetaDataBox()

@bindings.add(".")
def _stopSong(event):
    "Stop Currently Playing Song"
    music_controls.stopSong()

    music_controls.status = handler.status.content.text = 'IDLE'
    handler.play_pause.content.text = '|>'

    handler.current_song_time.content.text = '0:0'
    handler.total_song_time.content.text = '0:0'
    handler.song_progress.content.text = '0 %'

    handler.music_detail.text = ''
    handler.full_meta_data.content.text = ''

@bindings.add("space")
def _playPause(event):
    "Pause/Play Song"

    
    if music_controls.status=='playing':
        music_controls.pauseSong()
        music_controls.status = handler.status.content.text = 'paused'
        
        handler.play_pause.content.text = '|>'
        

    elif music_controls.status=='paused':
        music_controls.unpauseSong()
        music_controls.status = handler.status.content.text = 'playing'
        handler.play_pause.content.text = '||'

    elif music_controls.status=='IDLE':
        music_controls.loadSong()
        music_controls.playSong()

        
        
    

@bindings.add("n")
def _nextSong(event):
    "Next Song"
    music_controls.nextSong()

@bindings.add("p")
def _nextSong(event):
    "Next Song"
    music_controls.previousSong()

@bindings.add("o")
def _openSongFile(event):
    "Open MP3 song"
    handler.loadMusic()

@bindings.add("f")
def _selectSongDirectory(event):
    "Select Music Directory/Folder"
    music_player_controls.selectMusicDirectory()

#
# The menu container.
#

class MusicPlayerControls:
    def __init__(self):
        self.song_list = []
        self.song_directory_path = ''
        self.song_list = []

    def about(self):
        '''
        Show About Message Details
        '''   
        handler.show_message("About", "MP3 Music Player.\nCreated by Arijit Bhowmick.\n[sys41x4]")

    def selectMusicDirectory(self):

        async def coroutine():
            open_dialog = TextInputDialog(
                title=handler.header_text,
                label_text="Enter MP3 Music Directory Path:",
                completer=PathCompleter(),
            )

            path = await handler.show_dialog_as_float(open_dialog)
            ApplicationState.current_path = path

            if path is not None:
                try:
                    music_controls.loadSongPaths(os.path.join(path), 'dir')
                except OSError as e:
                    handler.show_message("Error", f"{e}")

        ensure_future(coroutine())

music_player_controls = MusicPlayerControls()

root_container = MenuContainer(
    body=body,
    menu_items=[
        MenuItem(
            "File",
            children=[
                MenuItem("Load MP3 file", handler=handler.loadMusic),
                MenuItem("Open Directory", handler=music_player_controls.selectMusicDirectory),
                MenuItem("-", disabled=True),
                MenuItem("Exit", handler=handler.exitApp),
            ],
        ),
        MenuItem(
            "Info",
            children=[
                MenuItem("META-DATA", handler=handler.showMetaDataBox),
                MenuItem("About", handler=music_player_controls.about),
                MenuItem("Help", handler=handler.help),
            ],
        ),
    ],
    floats=[
        Float(
            xcursor=True,
            ycursor=True,
            content=CompletionsMenu(max_height=16, scroll_offset=1),
        ),
    ],
    key_bindings=bindings,
)

style = Style.from_dict(
    {
        "dialog.body select-box": "bg:#cccccc",
        "dialog.body select-box": "bg:#cccccc",
        "dialog.body select-box cursor-line": "nounderline bg:ansired fg:ansiwhite",
        "dialog.body select-box last-line": "underline",
        "dialog.body text-area": "bg:#4444ff fg:white",
        "dialog.body text-area": "bg:#4444ff fg:white",
        "dialog.body radio-list radio": "bg:#4444ff fg:white",
        "dialog.body checkbox-list checkbox": "bg:#4444ff fg:white",
        "status": "reverse",
        "shadow": "bg:#440044",
    }
)


layout = Layout(root_container, focused_element=handler.text_field)




application = Application(
    layout=layout,
    enable_page_navigation_bindings=True,
    style=style,
    mouse_support=True,
    full_screen=True,
)


def run():
    application.run()


if __name__ == "__main__":
    run()
