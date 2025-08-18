#include "constants.h"

const std::string Constants::CACHE_DIR = "/tmp/minimize-state";
const std::string Constants::CACHE_FILE = Constants::CACHE_DIR + "/windows.json";
const std::string Constants::PREVIEW_DIR = "/tmp/window-previews";
const std::string Constants::LOCK_FILE = "/tmp/hyprtabs.lock";
const std::string Constants::FIFO_FILE = "/tmp/hyprtabs.fifo";

const std::unordered_map<std::string, std::string>& Constants::getIcons() {
    static const std::unordered_map<std::string, std::string> icons = {
        {"microsoft-edge", ""},
        {"discord", "󰙯"},
        {"code", "󰨞"},
        {"spotify", ""},
        {"default", "󰖲"}
    };
    return icons;
}
