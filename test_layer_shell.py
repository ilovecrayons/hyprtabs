#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, GtkLayerShell

def main():
    window = Gtk.Window()
    window.set_title("Test Layer Shell")
    
    # Initialize layer shell
    GtkLayerShell.init_for_window(window)
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.OVERLAY)
    GtkLayerShell.set_namespace(window, "test")
    GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.EXCLUSIVE)
    
    # Add some content
    label = Gtk.Label("Test Layer Shell Window")
    window.add(label)
    
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    
    print("Layer shell window created successfully")
    Gtk.main()

if __name__ == "__main__":
    main()
