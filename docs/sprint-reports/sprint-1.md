# Sprint 1 Report (08/18/2025 - 10/05/2025)

## [YouTube link of Sprint 1 Video](https://youtu.be/vEXFhcaj8qY)

## What's New (User Facing)
 * Completed Requirements and Specifications document including system requirements, use cases, and functional/non-functional requirements
 * Defined functional requirements covering API interface, content analysis, and dispute management
 * Defined non-functional requirements addressing scalability, containerization, performance, and security
 * Created user stories with acceptance scenarios covering recruiter workflows, candidate dispute process, developer testing, and system monitoring
 * Developed use cases with complete flow documentation
 * Identified cost-effective voice generation solution with accent and speech pattern variability for dataset creation
 * Established Lightning.ai shared development environment for collaborative coding with configurable hardware

## Work Summary (Developer Facing)
This sprint focused on translating our initial project vision into actionable requirements. We conducted multiple collaborative sessions to refine our understanding of the authenticity detection service, working closely as a team to ensure all stakeholder needs were captured. A key achievement was using GenAI as a brainstorming tool to identify gaps in our requirements. We also selected Lightning.ai as our shared development environment to enable collaborative coding with flexible GPU allocation, and identifying affordable realistic voice generators that support accent variation and speech parameter control (speed, tone, volume) for synthetic dataset generation. Our data strategy crystallized around using interview transcript dumps in Q&A format, which we'll process through voice generators with randomized accents and speech instructions (fast/slow, calm/quiet, etc.) to create labeled training data with ground-truth authenticity labels.

## Completed Issues/User Stories
Here are links to the issues that we completed in this sprint:

 * [Requirements and Specifications Document](https://github.com/vsevolod-kovalev/SymbalAI/issues/20)
 * [Functional Requirements Definition](https://github.com/vsevolod-kovalev/SymbalAI/issues/21)
 * [Non-Functional Requirements Definition](https://github.com/vsevolod-kovalev/SymbalAI/issues/22)
 * [User Stories with Acceptance Scenarios](https://github.com/vsevolod-kovalev/SymbalAI/issues/23)
 * [Use Cases and UML Diagrams](https://github.com/vsevolod-kovalev/SymbalAI/issues/24)
 
 ## Incomplete Issues/User Stories
 Here are links to issues we worked on but did not complete in this sprint:
 
 * [Functional Requirements Implementation (FR-01 through FR-10)](https://github.com/vsevolod-kovalev/SymbalAI/issues/3) - Requirements fully documented this sprint and implementation scheduled for future sprints following phased development plan.
 * [Non-Functional Requirements Implementation (NFR-01 through NFR-06)](https://github.com/vsevolod-kovalev/SymbalAI/issues/13) - Requirements fully documented this sprint and implementation scheduled for future sprints once core infrastructure is in place.
 * [Lightning.ai Development Environment Setup](https://github.com/vsevolod-kovalev/SymbalAI/issues/25) - Environment was selected and configured and granting individual team member access and hardware allocation protocols deferred to align with active development phases.

## Code Files for Review
Please review the following code files, which were actively developed during this sprint, for quality:
 * [Proper FastAPI structure](https://github.com/vsevolod-kovalev/SymbalAI/tree/555c584831c7627bec3f913a1bb8a3538561df0b/code/backend/src)
 
## Retrospective Summary
Here's what went well:
  * Strong team collaboration: Regular brainstorming sessions ensured all team members contributed to requirement definitions and caught potential gaps early
  * Effective use of GenAI: Using Gemini and GPT-5 for requirements review helped us identify missing edge cases and improve technical precision
  * Comprehensive documentation: Created detailed use cases with clear pre/post-conditions and alternative flows that will guide implementation
  * Clear stakeholder identification: Successfully mapped requirements to specific stakeholder needs

Here's what we'd like to improve:
   * Earlier GenAI integration: While GenAI was helpful, integrating it earlier in the requirements drafting process could have saved iteration time
   * More specific acceptance criteria: Some user story acceptance scenarios could benefit from more quantifiable success metrics
  
Here are changes we plan to implement in the next sprint:
   * Configure Lightning.ai workspace: Grant all team members access and establish hardware allocation protocols for training and testing
   * Generate synthetic training dataset: Process interview transcript dumps through voice generators with randomized accents and speech parameters (fast/slow, calm/quiet, etc.), creating labeled samples with ground-truth authenticity markers
   * Develop initial text analysis pipeline: Implement perplexity, burstiness, and repetition pattern detection
