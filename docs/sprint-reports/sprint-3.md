# Sprint 3 Report (11/06/2025 - 12/07/2025)

## [YouTube link of Sprint 3 Video](https://youtu.be/KMM6EtqOvrw)

## What's New (User Facing)
* A complete frontend interface for audio recording, uploading, playback, and displaying detection scores
* End-to-end audio authenticity detection using Branch A (naturalness/reading likelihood), Branch B (synthetic audio probability), and an integrated Combined Risk Score
* Clear risk labels (“Low”, “Medium”, “High”) and visual score presentation in the UI
* Fully functional /detect/audio endpoint with ML inference
* Enhanced input validation and error handling for audio analysis

## Work Summary (Developer Facing)
This sprint delivered a fully working prototype by integrating the backend ML pipelines with a frontend interface. We completed implementation of the audio detection API, combined scoring logic, Whisper-based feature extraction for Branch A, and WavLM inference for Branch B. The frontend was completed to support recording, uploading, analyzing, and visualizing results in real time. We focused on stabilizing the audio pipeline and ensuring seamless frontend–backend communication, producing a demonstrable and maintainable system aligned with client feedback prioritizing audio detection.

## Completed Issues/User Stories
Here are links to the issues that we completed in this sprint:

* [Testing and Acceptance Plans Document](https://github.com/vsevolod-kovalev/SymbalAI/issues/46)
* [Frontend Implementation for Audio Detection UI](https://github.com/vsevolod-kovalev/SymbalAI/issues/44)
* [Frontend–Backend Integration for Audio Detection](https://github.com/vsevolod-kovalev/SymbalAI/issues/45)
* [FR-03: Audio Input Processing](https://github.com/vsevolod-kovalev/SymbalAI/issues/5), [FR-04: Input Validation](https://github.com/vsevolod-kovalev/SymbalAI/issues/6), [FR-05: Response Format](https://github.com/vsevolod-kovalev/SymbalAI/issues/7)
* [NFR-01: Scalability](https://github.com/vsevolod-kovalev/SymbalAI/issues/13), [NFR-04: Cost Control](https://github.com/vsevolod-kovalev/SymbalAI/issues/16), [NFR-05: Maintainability](https://github.com/vsevolod-kovalev/SymbalAI/issues/17), [NFR-07: Performance](https://github.com/vsevolod-kovalev/SymbalAI/issues/19)

## Incomplete Issues/User Stories
Here are links to issues we worked on but did not complete in this sprint:
 
* [FR-02: Text Input Processing](https://github.com/vsevolod-kovalev/SymbalAI/issues/4) - Not implemented because the sprint focused on audio detection.
* [FR-06: LLM API Usage](https://github.com/vsevolod-kovalev/SymbalAI/issues/8) - Deferred because the system currently does not rely on any external LLM APIs.
* [FR-07: Text Analysis Features](https://github.com/vsevolod-kovalev/SymbalAI/issues/9) - Partial stubs exist. however, the client wants to focus on audio-based detection. Text features will be revisited only if the client confirms this FR is needed next semester.
* [FR-08: Authentication & Rate Limiting](https://github.com/vsevolod-kovalev/SymbalAI/issues/10) - Deferred because the prototype webpage is mainly for testing ML model performance.
* [FR-09: Dispute Workflow](https://github.com/vsevolod-kovalev/SymbalAI/issues/11) - Endpoint exists, but we prioritized detection features. Additional workflow implementation will be addressed later depending on client direction.
* [FR-10: Testing Framework](https://github.com/vsevolod-kovalev/SymbalAI/issues/12) - Not completed, because the sprint focused on functional audio analysis rather than building a full test infrastructure.
* [NFR-03: Cost Efficiency](https://github.com/vsevolod-kovalev/SymbalAI/issues/15) - Not applicable at this stage, since the system does not use external LLM APIs or paid inference services.
* [NFR-06: Security](https://github.com/vsevolod-kovalev/SymbalAI/issues/18) - As the prototype is a testing purpose only. All data is processed temporarily without storage, so full security hardening was not required.

## Code Files for Review
Please review the following code files, which were actively developed during this sprint, for quality:

**Frontend – Audio Detection UI**
* [code/frontend/src/pages/CheatingDetection/CheatingDetection.tsx](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/frontend/src/pages/CheatingDetection/CheatingDetection.tsx)
* [code/frontend/src/pages/CheatingDetection/AnalysisResults.tsx](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/frontend/src/pages/CheatingDetection/AnalysisResults.tsx)
* [code/frontend/src/components/RecordingCard/RecordingCard.tsx](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/frontend/src/components/RecordingCard/RecordingCard.tsx)

**Backend Detection Pipeline**
* [code/backend/src/api/detect.py](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/backend/src/api/detect.py) - audio endpoint, schema definitions
* [code/backend/src/services/audio_analyzer.py](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/backend/src/services/audio_analyzer.py) - combined inference logic
* [code/backend/src/services/branch_a_reader.py](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/backend/src/services/branch_a_reader.py) - Whisper ASR + prosody/naturalness scoring
* [ML/branch_b_infer.py](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/ML/branch_b_infer.py) - WavLM synthetic audio detection model

**Internal & API System**
* [code/backend/src/api/internal.py](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/backend/src/api/internal.py) - test + monitor endpoints
* [code/backend/src/main.py](https://github.com/vsevolod-kovalev/SymbalAI/blob/ab4b8b1f3dae383d71435db6e215aab5bbf28b45/code/backend/src/main.py) - routing, CORS, API configuration

## Retrospective Summary
Here's what went well:
* Achieved a full prototype, integrating both ML pipelines and frontend UI.
* Team collaboration was strong and aligned with client feedback.
* Backend demonstrated stable performance and consistent scoring outputs.


Here's what we'd like to improve:
* Need optimization of Whisper inference for faster scoring.
* More automated testing is required to prevent regressions during integration.
* Branch A calibration still needs tuning for borderline scripted speech.
  
Here are changes we plan to implement in the next sprint:
* Improve ML datasets, fine-tune Branch A and Branch B models, and enhance calibration.
* Expand frontend to dispute workflow functionality.
* Introduce CI/CD workflows and automated testing coverage.
