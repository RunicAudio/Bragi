[1mdiff --git a/src/core/app_state.py b/src/core/app_state.py[m
[1mindex a5cf191..05006b8 100644[m
[1m--- a/src/core/app_state.py[m
[1m+++ b/src/core/app_state.py[m
[36m@@ -93,6 +93,10 @@[m [mclass AppState:[m
         if listener not in self._gamification_listeners:[m
             self._gamification_listeners.append(listener)[m
 [m
[32m+[m[32m    def add_gamification_listener(self, listener: Callable[[], None]) -> None:[m
[32m+[m[32m        """Register a listener for gamification state changes."""[m
[32m+[m[32m        self.subscribe_gamification(listener)[m
[32m+[m
     def notify_view_changed(self) -> None:[m
         for listener in list(self._view_listeners):[m
             try:[m
[1mdiff --git a/src/domain/chord_definitions.py b/src/domain/chord_definitions.py[m
[1mindex 6d92a5d..7e46350 100644[m
[1m--- a/src/domain/chord_definitions.py[m
[1m+++ b/src/domain/chord_definitions.py[m
[36m@@ -8,6 +8,7 @@[m [mimport random[m
 from enum import Enum[m
 from typing import List, Optional, Tuple[m
 from pydantic import BaseModel, ConfigDict[m
[32m+[m[32mfrom domain.note_spelling import spell_interval[m
 [m
 [m
 class ChordQuality(str, Enum):[m
[36m@@ -77,6 +78,16 @@[m [mCHORD_INTERVAL_OFFSETS = {[m
     "Diminished": [0, 3, 6],[m
 }[m
 [m
[32m+[m[32mCHORD_DIATONIC_INTERVALS = {[m
[32m+[m[32m    "Major": [1, 3, 5],[m
[32m+[m[32m    "Minor": [1, 3, 5],[m
[32m+[m[32m    "Dominant 7th": [1, 3, 5, 7],[m
[32m+[m[32m    "Major 7th": [1, 3, 5, 7],[m
[32m+[m[32m    "Minor 7th": [1, 3, 5, 7],[m
[32m+[m[32m    "Sus4": [1, 4, 5],[m
[32m+[m[32m    "Sus2": [1, 2, 5],[m
[32m+[m[32m    "Diminished": [1, 3, 5],[m
[32m+[m[32m}[m
 [m
 def get_chord_pitch_classes(root_note: str, quality_str: str) -> List[int]:[m
     """Calculates pitch class integers (0..11) for a root and chord quality."""[m
[36m@@ -85,6 +96,54 @@[m [mdef get_chord_pitch_classes(root_note: str, quality_str: str) -> List[int]:[m
     offsets = CHORD_INTERVAL_OFFSETS.get(quality_str, [0, 4, 7])[m
     return [(root_pc + offset) % 12 for offset in offsets][m
 [m
[32m+[m[32mdef get_chord_note_names([m
[32m+[m[32m    root_note: str,[m
[32m+[m[32m    quality_str: str,[m
[32m+[m[32m    unicode_accidentals: bool = False,[m
[32m+[m[32m) -> List[str]:[m
[32m+[m[32m    """[m
[32m+[m[32m    Return correctly spelled chord tones.[m
[32m+[m
[32m+[m[32m    Uses diatonic interval numbers to preserve correct note-letter[m
[32m+[m[32m    relationships and chromatic offsets to determine accidentals.[m
[32m+[m
[32m+[m[32m    Examples:[m
[32m+[m[32m        get_chord_note_names("C", "Major")[m
[32m+[m[32m            -> ["C", "E", "G"][m
[32m+[m
[32m+[m[32m        get_chord_note_names("Db", "Major")[m
[32m+[m[32m            -> ["Db", "F", "Ab"][m
[32m+[m
[32m+[m[32m        get_chord_note_names("Bb", "Minor")[m
[32m+[m[32m            -> ["Bb", "Db", "F"][m
[32m+[m
[32m+[m[32m    Raises:[m
[32m+[m[32m        ValueError: If the root note or chord quality is unsupported.[m
[32m+[m[32m    """[m
[32m+[m[32m    if quality_str not in CHORD_INTERVAL_OFFSETS:[m
[32m+[m[32m        raise ValueError(f"Unsupported chord quality: {quality_str}")[m
[32m+[m
[32m+[m[32m    offsets = CHORD_INTERVAL_OFFSETS[quality_str][m
[32m+[m[32m    interval_numbers = CHORD_DIATONIC_INTERVALS[quality_str][m
[32m+[m
[32m+[m[32m    if len(offsets) != len(interval_numbers):[m
[32m+[m[32m        raise ValueError([m
[32m+[m[32m            f"Inconsistent interval definitions for {quality_str}"[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m    return [[m
[32m+[m[32m        spell_interval([m
[32m+[m[32m            root_note=root_note,[m
[32m+[m[32m            interval_number=interval_number,[m
[32m+[m[32m            semitones=semitones,[m
[32m+[m[32m            unicode_accidentals=unicode_accidentals,[m
[32m+[m[32m        )[m
[32m+[m[32m        for interval_number, semitones in zip([m
[32m+[m[32m            interval_numbers,[m
[32m+[m[32m            offsets,[m
[32m+[m[32m        )[m
[32m+[m[32m    ][m
[32m+[m
 def get_available_chord_names() -> List[str]:[m
     """Return every supported root and chord-quality combination."""[m
     from domain.music_theory import CHROMATIC_SHARPS[m
[1mdiff --git a/src/domain/music_theory.py b/src/domain/music_theory.py[m
[1mindex a35edcb..3d5bce5 100644[m
[1m--- a/src/domain/music_theory.py[m
[1m+++ b/src/domain/music_theory.py[m
[36m@@ -1,45 +1,127 @@[m
 """[m
 src/domain/music_theory.py[m
 ==========================[m
[31m-Fundamental music theory domain rules, chromatic mappings, frequency math, and scale/chord formulas.[m
[32m+[m[32mFundamental music theory domain rules, chromatic mappings,[m
[32m+[m[32mfrequency math, and note spelling.[m
 """[m
 [m
 import math[m
 from typing import Tuple[m
 [m
[31m-CHROMATIC_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][m
[32m+[m
[32m+[m[32mCHROMATIC_SHARPS = [[m
[32m+[m[32m    "C", "C#", "D", "D#", "E", "F",[m
[32m+[m[32m    "F#", "G", "G#", "A", "A#", "B"[m
[32m+[m[32m][m
[32m+[m
[32m+[m[32mCHROMATIC_FLATS = [[m
[32m+[m[32m    "C", "Db", "D", "Eb", "E", "F",[m
[32m+[m[32m    "Gb", "G", "Ab", "A", "Bb", "B"[m
[32m+[m[32m][m
[32m+[m
[32m+[m[32mNATURAL_NOTE_PITCH_CLASSES = {[m
[32m+[m[32m    "C": 0,[m
[32m+[m[32m    "D": 2,[m
[32m+[m[32m    "E": 4,[m
[32m+[m[32m    "F": 5,[m
[32m+[m[32m    "G": 7,[m
[32m+[m[32m    "A": 9,[m
[32m+[m[32m    "B": 11,[m
[32m+[m[32m}[m
 [m
 [m
 class MusicTheory:[m
[31m-    """Static utility methods for pitch class calculation and frequency conversions."""[m
[32m+[m[32m    """Static utility methods for pitch classes and frequency conversion."""[m
 [m
     A4_FREQ = 440.0[m
     A4_MIDI = 69[m
 [m
     @staticmethod[m
     def note_to_pitch_class(note_name: str) -> int:[m
[31m-        clean_note = note_name.strip().upper()[m
[31m-        if clean_note in CHROMATIC_SHARPS:[m
[31m-            return CHROMATIC_SHARPS.index(clean_note)[m
[31m-        return -1[m
[32m+[m[32m        """[m
[32m+[m[32m        Convert a note name into a pitch class (0-11).[m
[32m+[m
[32m+[m[32m        Supports natural notes, sharps, flats, and enharmonic spellings.[m
[32m+[m[32m        Returns -1 for invalid input.[m
[32m+[m[32m        """[m
[32m+[m
[32m+[m[32m        if not isinstance(note_name, str):[m
[32m+[m[32m            return -1[m
[32m+[m
[32m+[m[32m        clean_note = note_name.strip()[m
[32m+[m
[32m+[m[32m        if not clean_note:[m
[32m+[m[32m            return -1[m
[32m+[m
[32m+[m[32m        # Normalize Unicode accidental symbols.[m
[32m+[m[32m        clean_note = clean_note.replace("♯", "#").replace("♭", "b")[m
[32m+[m
[32m+[m[32m        letter = clean_note[0].upper()[m
[32m+[m[32m        accidental = clean_note[1:][m
[32m+[m
[32m+[m[32m        if letter not in NATURAL_NOTE_PITCH_CLASSES:[m
[32m+[m[32m            return -1[m
[32m+[m
[32m+[m[32m        natural_pc = NATURAL_NOTE_PITCH_CLASSES[letter][m
[32m+[m
[32m+[m[32m        if accidental == "":[m
[32m+[m[32m            offset = 0[m
[32m+[m[32m        elif accidental == "#":[m
[32m+[m[32m            offset = 1[m
[32m+[m[32m        elif accidental == "b":[m
[32m+[m[32m            offset = -1[m
[32m+[m[32m        else:[m
[32m+[m[32m            return -1[m
[32m+[m
[32m+[m[32m        return (natural_pc + offset) % 12[m
 [m
     @staticmethod[m
[31m-    def pitch_class_to_note(pitch_class: int) -> str:[m
[31m-        return CHROMATIC_SHARPS[pitch_class % 12][m
[32m+[m[32m    def pitch_class_to_note([m
[32m+[m[32m        pitch_class: int,[m
[32m+[m[32m        prefer_flats: bool = False[m
[32m+[m[32m    ) -> str:[m
[32m+[m[32m        """[m
[32m+[m[32m        Convert a pitch class into a note name.[m
[32m+[m
[32m+[m[32m        Sharp notation is the default for backward compatibility.[m
[32m+[m[32m        Set prefer_flats=True to use flat spellings.[m
[32m+[m[32m        """[m
[32m+[m
[32m+[m[32m        note_names = CHROMATIC_FLATS if prefer_flats else CHROMATIC_SHARPS[m
[32m+[m
[32m+[m[32m        return note_names[pitch_class % 12][m
 [m
     @staticmethod[m
[31m-    def frequency_to_note_info(freq: float) -> Tuple[str, int, float]:[m
[32m+[m[32m    def frequency_to_note_info([m
[32m+[m[32m        freq: float,[m
[32m+[m[32m        prefer_flats: bool = False[m
[32m+[m[32m    ) -> Tuple[str, int, float]:[m
[32m+[m[32m        """[m
[32m+[m[32m        Convert frequency into note name, pitch class, and cents deviation.[m
[32m+[m
[32m+[m[32m        Sharp notation remains the default.[m
[32m+[m[32m        """[m
[32m+[m
         if freq <= 0:[m
             return ("--", -1, 0.0)[m
 [m
[31m-        # MIDI Note Number calculation[m
[31m-        midi_num = 12 * math.log2(freq / MusicTheory.A4_FREQ) + MusicTheory.A4_MIDI[m
[32m+[m[32m        midi_num = ([m
[32m+[m[32m            12 * math.log2(freq / MusicTheory.A4_FREQ)[m
[32m+[m[32m            + MusicTheory.A4_MIDI[m
[32m+[m[32m        )[m
[32m+[m
         nearest_midi = round(midi_num)[m
         pitch_class = nearest_midi % 12[m
[31m-        note_name = CHROMATIC_SHARPS[pitch_class][m
 [m
[31m-        # Cents deviation calculation[m
[31m-        nearest_freq = MusicTheory.A4_FREQ * (2 ** ((nearest_midi - MusicTheory.A4_MIDI) / 12))[m
[32m+[m[32m        note_name = MusicTheory.pitch_class_to_note([m
[32m+[m[32m            pitch_class,[m
[32m+[m[32m            prefer_flats=prefer_flats[m
[32m+[m[32m        )[m
[32m+[m
[32m+[m[32m        nearest_freq = MusicTheory.A4_FREQ * ([m
[32m+[m[32m            2 ** ((nearest_midi - MusicTheory.A4_MIDI) / 12)[m
[32m+[m[32m        )[m
[32m+[m
         cents = 1200 * math.log2(freq / nearest_freq)[m
 [m
         return (note_name, pitch_class, cents)[m
[1mdiff --git a/tests/test_chord_definitions.py b/tests/test_chord_definitions.py[m
[1mindex 71fb27e..d24fa2b 100644[m
[1m--- a/tests/test_chord_definitions.py[m
[1m+++ b/tests/test_chord_definitions.py[m
[36m@@ -1,4 +1,5 @@[m
 import pytest[m
[32m+[m[32mfrom domain.note_spelling import parse_note[m
 [m
 from domain.chord_definitions import ([m
     CHORD_INTERVAL_OFFSETS,[m
[36m@@ -9,6 +10,7 @@[m [mfrom domain.chord_definitions import ([m
     ChordDefinition,[m
     TargetChord,[m
     get_chord_pitch_classes,[m
[32m+[m[32m    get_chord_note_names,[m
     get_available_chord_names,[m
     select_random_chord,[m
 )[m
[36m@@ -224,3 +226,71 @@[m [mclass TestChordModels:[m
 [m
         with pytest.raises(Exception):[m
             target.required_voicing = None[m
[32m+[m
[32m+[m[32mclass TestChordNoteSpelling:[m
[32m+[m
[32m+[m[32m    @pytest.mark.parametrize([m
[32m+[m[32m        "root,quality,expected",[m
[32m+[m[32m        [[m
[32m+[m[32m            ("C", "Major", ["C", "E", "G"]),[m
[32m+[m[32m            ("D", "Minor", ["D", "F", "A"]),[m
[32m+[m[32m            ("E", "Dominant 7th", ["E", "G#", "B", "D"]),[m
[32m+[m[32m            ("F", "Major 7th", ["F", "A", "C", "E"]),[m
[32m+[m[32m            ("A", "Minor 7th", ["A", "C", "E", "G"]),[m
[32m+[m[32m            ("C", "Sus4", ["C", "F", "G"]),[m
[32m+[m[32m            ("C", "Sus2", ["C", "D", "G"]),[m
[32m+[m[32m            ("B", "Diminished", ["B", "D", "F"]),[m
[32m+[m[32m        ],[m
[32m+[m[32m    )[m
[32m+[m[32m    def test_all_chord_qualities_spell_correctly([m
[32m+[m[32m        self, root, quality, expected[m
[32m+[m[32m    ):[m
[32m+[m[32m        assert get_chord_note_names(root, quality) == expected[m
[32m+[m
[32m+[m[32m    @pytest.mark.parametrize([m
[32m+[m[32m        "root,quality,expected",[m
[32m+[m[32m        [[m
[32m+[m[32m            ("Db", "Major", ["Db", "F", "Ab"]),[m
[32m+[m[32m            ("F#", "Major", ["F#", "A#", "C#"]),[m
[32m+[m[32m            ("Bb", "Minor", ["Bb", "Db", "F"]),[m
[32m+[m[32m            ("Eb", "Minor", ["Eb", "Gb", "Bb"]),[m
[32m+[m[32m            ("G#", "Major", ["G#", "B#", "D#"]),[m
[32m+[m[32m            ("Ab", "Major", ["Ab", "C", "Eb"]),[m
[32m+[m[32m            ("C#", "Major", ["C#", "E#", "G#"]),[m
[32m+[m[32m            ("Gb", "Major", ["Gb", "Bb", "Db"]),[m
[32m+[m[32m        ],[m
[32m+[m[32m    )[m
[32m+[m[32m    def test_enharmonic_roots_preserve_correct_spelling([m
[32m+[m[32m        self, root, quality, expected[m
[32m+[m[32m    ):[m
[32m+[m[32m        assert get_chord_note_names(root, quality) == expected[m
[32m+[m
[32m+[m[32m    def test_unicode_accidental_output(self):[m
[32m+[m[32m        assert get_chord_note_names([m
[32m+[m[32m            "Db", "Major", unicode_accidentals=True[m
[32m+[m[32m        ) == ["D♭", "F", "A♭"][m
[32m+[m
[32m+[m[32m    def test_rejects_unsupported_quality(self):[m
[32m+[m[32m        with pytest.raises(ValueError):[m
[32m+[m[32m            get_chord_note_names("C", "Augmented")[m
[32m+[m
[32m+[m[32m    def test_rejects_invalid_root(self):[m
[32m+[m[32m        with pytest.raises(ValueError):[m
[32m+[m[32m            get_chord_note_names("H", "Major")[m
[32m+[m
[32m+[m[32m    def test_chord_spelling_preserves_existing_pitch_classes(self):[m
[32m+[m[32m        roots = ["C", "Db", "F#", "Bb", "Eb", "G#"][m
[32m+[m
[32m+[m[32m        for root in roots:[m
[32m+[m[32m            for quality, offsets in CHORD_INTERVAL_OFFSETS.items():[m
[32m+[m[32m                notes = get_chord_note_names(root, quality)[m
[32m+[m
[32m+[m[32m                pitch_classes = [[m
[32m+[m[32m                    parse_note(note).pitch_class[m
[32m+[m[32m                    for note in notes[m
[32m+[m[32m                ][m
[32m+[m
[32m+[m[32m                assert pitch_classes == get_chord_pitch_classes([m
[32m+[m[32m                    root, quality[m
[32m+[m[32m                )[m
[32m+[m[32m                assert len(notes) == len(offsets)[m
[1mdiff --git a/tests/test_music_theory.py b/tests/test_music_theory.py[m
[1mindex dad28fe..058a535 100644[m
[1m--- a/tests/test_music_theory.py[m
[1m+++ b/tests/test_music_theory.py[m
[36m@@ -34,7 +34,7 @@[m [mclass TestNoteToPitchClass:[m
     def test_whitespace_is_ignored(self):[m
         assert MusicTheory.note_to_pitch_class(" C ") == 0[m
 [m
[31m-    @pytest.mark.parametrize("note", ["H", "X", "", "Db", "Bb"])[m
[32m+[m[32m    @pytest.mark.parametrize("note", ["H", "X", "", "Invalid", "C##", "Dbb"])[m
     def test_invalid_notes_return_negative_one(self, note):[m
         assert MusicTheory.note_to_pitch_class(note) == -1[m
 [m
[36m@@ -69,7 +69,66 @@[m [mclass TestPitchClassToNote:[m
         assert MusicTheory.pitch_class_to_note(-1) == "B"[m
         assert MusicTheory.pitch_class_to_note(-12) == "C"[m
 [m
[32m+[m[32mclass TestEnharmonicNoteSupport:[m
 [m
[32m+[m[32m    @pytest.mark.parametrize([m
[32m+[m[32m        "note, expected",[m
[32m+[m[32m        [[m
[32m+[m[32m            ("Db", 1),[m
[32m+[m[32m            ("Eb", 3),[m
[32m+[m[32m            ("Gb", 6),[m
[32m+[m[32m            ("Ab", 8),[m
[32m+[m[32m            ("Bb", 10),[m
[32m+[m[32m            ("C#", 1),[m
[32m+[m[32m            ("D#", 3),[m
[32m+[m[32m            ("F#", 6),[m
[32m+[m[32m            ("G#", 8),[m
[32m+[m[32m            ("A#", 10),[m
[32m+[m[32m            ("E#", 5),[m
[32m+[m[32m            ("Fb", 4),[m
[32m+[m[32m            ("B#", 0),[m
[32m+[m[32m            ("Cb", 11),[m
[32m+[m[32m        ],[m
[32m+[m[32m    )[m
[32m+[m[32m    def test_enharmonic_notes(self, note, expected):[m
[32m+[m[32m        assert MusicTheory.note_to_pitch_class(note) == expected[m
[32m+[m
[32m+[m[32m    def test_unicode_accidentals(self):[m
[32m+[m[32m        assert MusicTheory.note_to_pitch_class("C♯") == 1[m
[32m+[m[32m        assert MusicTheory.note_to_pitch_class("D♭") == 1[m
[32m+[m
[32m+[m[32m    def test_lowercase_flat_input(self):[m
[32m+[m[32m        assert MusicTheory.note_to_pitch_class("db") == 1[m
[32m+[m[32m        assert MusicTheory.note_to_pitch_class("bb") == 10[m
[32m+[m
[32m+[m[32mclass TestFlatNotation:[m
[32m+[m
[32m+[m[32m    @pytest.mark.parametrize([m
[32m+[m[32m        "pitch_class, expected",[m
[32m+[m[32m        [[m
[32m+[m[32m            (0, "C"),[m
[32m+[m[32m            (1, "Db"),[m
[32m+[m[32m            (2, "D"),[m
[32m+[m[32m            (3, "Eb"),[m
[32m+[m[32m            (4, "E"),[m
[32m+[m[32m            (5, "F"),[m
[32m+[m[32m            (6, "Gb"),[m
[32m+[m[32m            (7, "G"),[m
[32m+[m[32m            (8, "Ab"),[m
[32m+[m[32m            (9, "A"),[m
[32m+[m[32m            (10, "Bb"),[m
[32m+[m[32m            (11, "B"),[m
[32m+[m[32m        ],[m
[32m+[m[32m    )[m
[32m+[m[32m    def test_flat_pitch_class_names(self, pitch_class, expected):[m
[32m+[m[32m        assert MusicTheory.pitch_class_to_note([m
[32m+[m[32m            pitch_class,[m
[32m+[m[32m            prefer_flats=True[m
[32m+[m[32m        ) == expected[m
[32m+[m
[32m+[m[32m    def test_default_output_remains_sharp_based(self):[m
[32m+[m[32m        assert MusicTheory.pitch_class_to_note(1) == "C#"[m
[32m+[m[32m        assert MusicTheory.pitch_class_to_note(10) == "A#"[m
 class TestFrequencyToNoteInfo:[m
 [m
     @pytest.mark.parametrize([m
[36m@@ -121,3 +180,13 @@[m [mclass TestFrequencyToNoteInfo:[m
     def test_invalid_nonpositive_frequencies(self):[m
         assert MusicTheory.frequency_to_note_info(0) == ("--", -1, 0.0)[m
         assert MusicTheory.frequency_to_note_info(-100) == ("--", -1, 0.0)[m
[32m+[m
[32m+[m[32mdef test_frequency_conversion_supports_flat_notation():[m
[32m+[m[32m    note, pitch_class, cents = MusicTheory.frequency_to_note_info([m
[32m+[m[32m        277.18,[m
[32m+[m[32m        prefer_flats=True[m
[32m+[m[32m    )[m
[32m+[m
[32m+[m[32m    assert note == "Db"[m
[32m+[m[32m    assert pitch_class == 1[m
[32m+[m[32m    assert abs(cents) < 2.0[m
