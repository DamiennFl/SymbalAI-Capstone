# Sprint 5 Report (02/18/2026 - 03/15/2026)

## [YouTube Link of Sprint 5 Video](https://youtu.be/OyEqRENLpXY)

## What's New (User Facing)
* Continued improving the Branch B audio detection model and evaluating optimization techniques to improve runtime performance and model size.
* Implemented and tested ONNX-based INT8 quantized inference pipeline for CPU environments.
* Improved inference speed with optimized preprocessing and 8-second sliding window audio analysis.
* Achieved ~95% accuracy and ~0.97 AUC on external evaluation datasets while significantly reducing model size.
* Began experimentation with RabbitMQ message queue integration for asynchronous processing architecture.

## Work Summary (Developer Facing)
This sprint focused on improving model efficiency and exploring architectural improvements for scalability. We evaluated backbone model and tried DistilHuBERT based on the best trade-off between runtime performance, model size, and detection accuracy. Through experimentation we determined that an 8-second analysis window, unfreezing one transformer layer, and applying INT8 quantization provided strong performance while significantly reducing computational overhead. The quantized ONNX models retained nearly the same accuracy as FP32 models while reducing model size from approximately 90 MB to around 48 MB and enabling faster CPU inference. We also began exploring RabbitMQ as a potential improvement to the system architecture, allowing audio processing tasks to be handled asynchronously through message queues.

## Completed Issues/User Stories
Here are links to the issues that we completed in this sprint:

* [FR-02: Text Input Processing](https://github.com/vsevolod-kovalev/SymbalAI/issues/4)

* [FR-10: Testing Framework](https://github.com/vsevolod-kovalev/SymbalAI/issues/12)

* [Branch B Model Efficiency](https://github.com/vsevolod-kovalev/SymbalAI/issues/48)

* [Improve API Runtime Overhead](https://github.com/vsevolod-kovalev/SymbalAI/issues/49)

## Incomplete Issues/User Stories
Here are links to issues we worked on but did not complete in this sprint:
 
* [Research Paper](https://github.com/vsevolod-kovalev/SymbalAI/issues/50) - We have a rough draft of the paper, but not a finalized version.

* [Deployment with RabbitMQ](https://github.com/vsevolod-kovalev/SymbalAI/issues/51) - Initial experimentation was performed to evaluate asynchronous processing, but full integration into the system architecture was not completed during this sprint.

## Code Files for Review
Please review the following code files, which were actively developed during this sprint, for quality:

**Note:** The repository has been forked to Symbal AI’s private organizational repository. Access is restricted to Symbal AI employees and our capstone team members. The professor may request temporary access if review of the private repository is required.

Primary Files Modified During Sprint 5:
* Backend updates introducing RabbitMQ-based audio processing, separating the API service from the audio inference worker to improve deployment scalability and responsiveness.

**Repository Link (Private):** https://github.com/Symbal-AI/ai-cheat-detector/tree/KhangB-switch-to-onnx/code/backend

## Retrospective Summary
Here's what went well:
* Quantized ONNX models maintained strong accuracy while significantly reducing model size.
* Inference performance improvements allow the system to run efficiently even on lower-tier CPUs.

Here's what we'd like to improve:
* Integration between the optimized inference pipeline and the deployed API service still requires refinement.
* Architectural improvements such as asynchronous processing require additional design and testing.
  
Here are changes we plan to implement in the next sprint:
* Continue exploring RabbitMQ-based asynchronous processing for improved scalability.
* Further refine preprocessing and inference performance to reduce latency.
