<img width="1223" height="919" alt="image" src="https://github.com/user-attachments/assets/006192eb-615b-401e-84b4-111d5c6c2939" />


# Project Name
Symbal Jr: AI-Powered Response Authenticity Detection for Hiring

## Project summary

### One-sentence description of the project

We are using ML to create a microservice API that will accurately detect AI or script usage for candidate interviews, which will be integrated into Symbal AI's user flow.

### Additional information about the project

As hiring shifts toward remote and asynchronous interviews, powerful AI tools make it easy for
candidates to lean on generated text, read polished scripts, or even play back synthetic speech.
This blurs the signal that reviewers rely on to judge real communication skills and in the moment
reasoning, creating a trust gap for platforms like Symbal’s AI-enabled process. Our motivation is
to restore trust by giving reviewers evidence about authenticity rather than guesses.

Single channel detectors are not enough. Text only methods that look for model-like writing
patterns can be brittle on short, lightly edited answers, and watermarking only helps when the
model is under our control. On the audio side, deepfake and TTS detectors can miss unseen
synthesis methods and noisy real-world recordings. Research on read versus spontaneous
speech, however, shows prosodic and disfluency cues that help distinguish scripted delivery from
genuine answers, suggesting value in fusing complementary signals rather than trusting any one
test. Thus, it is increasingly important to create dedicated systems tailored to detect AI or script
usage.

## Installation

### Prerequisites

Currently, only FastAPI is required for the frontend code.

### Installation Guide

The most convenient way to install and use our current implementation is to navigate into ..\code\backend\ and then run `docker compose up` to start the container.
Additionally, if this is done on the Branch-A-Improvements-API-Integration branch, then it will spin up the API and also the Branch A implementation which can be 
used to transcribe and produce a confidence score, although this additionally requires [CUDA 12.2.x from Nvidia](https://developer.nvidia.com/cuda-12-2-2-download-archive) to run locally.


## License

See LICENSE.md
