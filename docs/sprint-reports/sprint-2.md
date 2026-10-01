# Sprint 2 Report (10/06/2025 - 11/05/2025)

## [YouTube link of Sprint 2 Video](https://youtu.be/X7lBVSua7rI)

## What's New (User Facing)
* Implemented RESTful API with functional endpoints
* Deployed interactive Swagger UI for API testing and documentation
* Built Branch A audio detection analyzing naturalness through prosody extraction, and disfluency detection in spontaneous speech
* Built Branch B audio detection focusing on synthetic audio identification using TTS artifact recognition and voice conversion pattern detection
* Created solution approach documentation covering system architecture design

## Work Summary (Developer Facing)
Sprint 2 focused on building our core detection system and establishing functional API endpoints. We implemented a FastAPI microservice with text and audio detection capabilities. We implemented the dual-branch audio pipeline, where Branch A evaluates speech naturalness through disfluency and prosody patterns while Branch B detects synthetic audio signatures, which together provide robust multi-dimensional audio authenticity assessment. The challenge was determining how to effectively combine these two branches into a unified score, as we initially lacked clarity on what the final result structure should look like and how to weight each branch's contribution appropriately.

## Completed Issues/User Stories
Here are links to the issues that we completed in this sprint:

 * [Project Solution Approach document](https://github.com/vsevolod-kovalev/SymbalAI/issues/27)
 * [Write Introduction & System Overview sections](https://github.com/vsevolod-kovalev/SymbalAI/issues/28)
 * [Document Architecture Design with UML and subsystem decomposition](https://github.com/vsevolod-kovalev/SymbalAI/issues/29)
 * [Document Data Design including models and persistence strategy](https://github.com/vsevolod-kovalev/SymbalAI/issues/30)
 * [Document User Interface Design and API access methods](https://github.com/vsevolod-kovalev/SymbalAI/issues/31)
 * [Write Dockerfile and docker-compose](https://github.com/vsevolod-kovalev/SymbalAI/issues/33)
 * [Train TTS artifact detection model](https://github.com/vsevolod-kovalev/SymbalAI/issues/38)
 * [Integrate ASR engine for audio transcription](https://github.com/vsevolod-kovalev/SymbalAI/issues/34)
 * [Implement prosody feature extraction](https://github.com/vsevolod-kovalev/SymbalAI/issues/35)
 * [Create disfluency detection module](https://github.com/vsevolod-kovalev/SymbalAI/issues/36)
 * [Build POST /detect/text endpoint with validation](https://github.com/vsevolod-kovalev/SymbalAI/issues/39)
 * [Build POST /detect/audio endpoint with file upload](https://github.com/vsevolod-kovalev/SymbalAI/issues/40)

## Incomplete Issues/User Stories
 Here are links to issues we worked on but did not complete in this sprint:
 
 * [Functional Requirements Implementation (FR-02 through FR-10)](https://github.com/vsevolod-kovalev/SymbalAI/issues/4) - Sprint 2 prioritized building the ML detection capabilities with Branch A and Branch B audio pipelines. Some functional requirements implementation will progress incrementally in Sprint 3.
 * [Non-Functional Requirements Implementation (NFR-01 through NFR-06)](https://github.com/vsevolod-kovalev/SymbalAI/issues/13) - Sprint 2 established Docker containerization (NFR-02). We focused on detection functionality rather than non-functional requirements. Sprint 3 will address remaining NFRs including.

## Code Files for Review
Please review the following code files, which were actively developed during this sprint, for quality:
 * [API Endpoints](https://github.com/vsevolod-kovalev/SymbalAI/tree/555c584831c7627bec3f913a1bb8a3538561df0b/code/backend/src) - Code for the endpoint implementations
 * [Branch A - Naturalness Detection](https://github.com/vsevolod-kovalev/SymbalAI/tree/7ccbaec1ce0b6c39b19c6ef18f392a185960643e/code/ML) - Code for the branch A
 * [Branch B - Synthetic Audio Detection](https://github.com/vsevolod-kovalev/SymbalAI/tree/dec7c14ec40e0658475f275758d1b1a426978534/ML/training/synth_generation) - Code for the branch B

## Retrospective Summary
Here's what went well:
  * Regular client meetings helped us stay on track and ensured our development direction matched their expectations and allowed us to adjust requirements based on their requirement.
  * Dividing work across detection subsystems, API development, and containerization let the team tackle multiple priorities simultaneously and deliver more in the same timeframe.
  * Dual-branch audio detection pipeline was built with Branch A evaluating naturalness indicators and Branch B identifying synthetic speech patterns.


Here's what we'd like to improve:
   * Training data needs expansion with more diverse samples to improve accuracy for both Branch A naturalness detection and Branch B synthetic audio identification.
   * Integration testing should be planned and executed earlier in the sprint to catch any issues before they become blocking problems.
   * Documentation needs to be maintained throughout development to facilitate team collaboration, knowledge sharing, and effective code review processes.
  
Here are changes we plan to implement in the next sprint:
   * Develop and implement effective fusion strategy to combine Branch A and Branch B outputs into a unified audio authenticity score.
   * Integrate complete ML detection pipeline into the API Gateway to enable seamless end-to-end processing from input to final authenticity assessment.
   * Enhance accuracy of both branches through additional training with expanded datasets and fine-tuning of detection thresholds and feature extraction methods.
