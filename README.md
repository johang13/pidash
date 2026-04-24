# pidash

[![Pylint](https://github.com/johang13/pidash/actions/workflows/pylint.yml/badge.svg?branch=main)](https://github.com/johang13/pidash/actions/workflows/pylint.yml?query=branch%3Amain)

## Introduction

A simple dashboard built with Python, using a Raspberry Pi Zero 2W and Waveshare 7.5inch E-Ink display. 
The dashboard displays the current time, date, weather information, and a random trivia fact.
---

## Installation

1. Enable SPI on the Raspberry Pi Zero:
   1. Run `sudo raspi-config`
   2. Navigate to `Interfacing Options` > `SPI` and enable it
   3. Alternatively, `sudo raspi-config nonint do_spi 0`
4. Reboot

Then simply clone the repository and run the `setup.sh` script to install the necessary dependencies.

```bash
git clone https://github.com/johang13/pidash.git
cd pidash
./setup.sh
```

### Verify

To verify the display works correctly, you can run the Waveshare example script, provided by the Waveshare library in the submodule.
A helper script has been put together to make it easier to run the example.

```bash
./example.sh
```

### Run

To run, simply execute the `run.sh` script.

```bash
./run.sh
```

## Local Development

It is advised to test and develop the dashboard on a local machine using the provided emulator.
The emulator simulates the E-Ink display and allows you to test the dashboard without risking damage to the hardware.

The code will automatically detect if it's running on a Raspberry Pi and use the appropriate display class.
If you're running it on a local machine, it will use the emulator.

### Environment Setup
 
This project uses [uv package manager](https://docs.astral.sh/uv/) for local development.

The following commands install `uv`, sync the project environment, and launch the dashboard in emulator mode.
```zsh
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
uv run pidash
```

## Acknowledgements

### Hardware
- [Raspberry Pi Zero 2W](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/) - The main hardware used for the project.
- [Waveshare E-Ink Display](https://www.waveshare.com/7.5inch-e-paper-hat.htm) - The hardware used for the dashboard.

### Software

- [Python](https://www.python.org/) - The programming language used for the project.
- [Waveshare Python Library](https://github.com/waveshareteam/e-Paper.git) - Used for interfacing with the E-Ink display.
- [OpenMeteo API](https://open-meteo.com/) - Used for fetching weather data.

### Third-Party Assets

- [Weather Icons](https://erikflowers.github.io/weather-icons/) - Used for displaying weather icons.
- [Open Sans Font](https://fonts.google.com/specimen/Open+Sans) - Used for displaying text on the dashboard.

See [assets/fonts](src/pidash/assets/fonts) for details on licenses and attributions for the fonts used in this project.