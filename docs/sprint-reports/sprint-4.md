# Sprint 4 Report (01/12/2026 - 02/17/2026)

## [YouTube Link of Sprint 4 Video](https://youtu.be/W09piT1q-n4)

## What's New (User Facing)
* Successfully deployed working version of the system on Symbal AI’s test servers
* Improved Branch B model efficiency (smaller size and reduced memory footprint)
* Optimized API runtime performance and reduced inference overhead
* Stabilized core text and audio authenticity detection pipeline
* Validated system functionality in client test environment

## Work Summary (Developer Facing)
This Sprint focused primarily on deployment stabilization, performance optimization, and client validation. We worked closely with Symbal AI to test deployment on their infrastructure, identifying performance bottlenecks and memory inefficiencies, particularly within Branch B. We refactored parts of the model loading and inference pipeline to reduce runtime overhead and improve responsiveness.

## Completed Issues/User Stories
Here are links to the issues that we completed in this sprint:

* [FR-07: Text Analysis Features](https://github.com/vsevolod-kovalev/SymbalAI/issues/9)
* [FR-08: Authentication & Rate Limiting](https://github.com/vsevolod-kovalev/SymbalAI/issues/10)
* [NFR-03: Cost Efficiency](https://github.com/vsevolod-kovalev/SymbalAI/issues/15)

## Incomplete Issues/User Stories
Here are links to issues we worked on but did not complete in this sprint:
 
* [FR-02: Text Input Processing](https://github.com/vsevolod-kovalev/SymbalAI/issues/4) - Text input processing is not a current priority, as we are focusing on improving performance and stabilizing our deployment.
* [FR-10: Testing Framework](https://github.com/vsevolod-kovalev/SymbalAI/issues/12) - This issue depends on deployment to the client’s servers so we can properly test the resiliency of the API microservice.
* [Branch B Model Efficiency](https://github.com/vsevolod-kovalev/SymbalAI/issues/48) - Ongoing optimization to reduce memory usage and model size
* [Improve API Runtime Overhead](https://github.com/vsevolod-kovalev/SymbalAI/issues/49) - Additional refactoring required to lower CPU and memory consumption.
* [Research Paper](https://github.com/vsevolod-kovalev/SymbalAI/issues/50) - We have a rough draft of the paper, but not a finalized version.

## Code Files for Review
Please review the following code files, which were actively developed during this sprint, for quality:

**Note:** The repository has been forked to Symbal AI’s private organizational repository. Access is restricted to Symbal AI employees and our capstone team members. The professor may request temporary access if review of the private repository is required.

Primary Files Modified During Sprint 4:
* Backend inference optimization modules (Branch B runtime improvements)
* Model compression and efficiency adjustments for Branch B
* API performance optimization and memory management updates
* Deployment configuration files (Docker/Kubernetes deployment scripts)

**Repository Link (Private):** https://github.com/Symbal-AI/ai-cheat-detector.git

## Retrospective Summary
Here's what went well:
* Achieved successful working deployment on client test servers.
* Improved model efficiency and reduced runtime overhead.
* Strong communication with client through regular Slack coordination.


Here's what we'd like to improve:
* Deployment consistency across environments needs automation.
* Model inference speed (especially Whisper-based Branch A) needs further tuning.
  
Here are changes we plan to implement in the next sprint:
* Further optimize model runtime speed and memory usage.
* Improve calibration and accuracy of detection models.
* Expand automated validation and monitoring.
