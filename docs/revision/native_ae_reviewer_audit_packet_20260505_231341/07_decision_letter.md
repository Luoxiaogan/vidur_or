
Dear authors (names omitted for double-blind review):

Manuscript ID OPRE-2025-04-1885, titled "Optimizing LLM Inference: Fluid-Guided Online Scheduling with Memory Constraints" which you submitted to Operations Research, has been reviewed and the decision is Major Revision.

Please see the reviews below and the AE report. The AE recommends reject-and-resubmit. I have placed a major revision (because we reserve reject-and-resubmit for papers that require a methodological overhaul, whereas I do not see that in the reports). However, consistent feedback is that the quality of exposition is very significantly below expectations, and the writing needs serious, conscientious revision. If these issues persist, I expect that the paper will be rejected by the team in the next round. So the revision is a "risky" major revision. The most negative reviewer points out that latency is largely overlooked, which is indeed a trade-off of modern AI inference, e.g., compared with search. Throughput is one goal, but not the only one.

The comments of the reviewer(s) are included at the bottom of this letter and in your Author Center at https://mc.manuscriptcentral.com/opre.

The reviewer(s) suggest some major revisions to your manuscript. Therefore, I invite you to respond to the reviewer(s)' comments and revise your manuscript.

To revise your manuscript, log into https://mc.manuscriptcentral.com/opre and enter your Author Center, where you will find your manuscript title listed under "Manuscripts with Decisions." Under "Actions," click on "Create a Revision." Your manuscript number will be appended to denote a revision.

When preparing your revision, please review the detailed submission guidelines at http://pubsonline.informs.org/page/opre/submission-guidelines. LaTeX style files are available at http://pubsonline.informs.org/authorportal/latex-style-files. All submissions must follow this style.

Once the revised manuscript is prepared, you can upload it and submit it through your Author Center.

When submitting your revised manuscript, you will be able to respond to the comments made by the reviewer(s) in the space provided. You can use this space to document any changes you make to the original manuscript. In order to expedite the processing of the revised manuscript, please be as specific as possible in your response to the reviewer(s).

IMPORTANT: Your original files are available to you when you upload your revised manuscript. Please delete any redundant files before completing the submission.

The journal expects authors to resubmit papers no later than 12 months after they receive the journal feedback. Otherwise, the journal may consider the revision as a new submission.

Once again, thank you for submitting your manuscript to Operations Research. I look forward to receiving your revision.

Sincerely,

Prof. Neil Walton
Area Editor, Operations Research
neil.walton@durham.ac.uk


Associate Editor's Comments to Author:
Associate Editor
Comments to Author:
(There are no comments.)


Referee's Comments to the author:
Referee: 1

Comments to the Author
(There are no comments.)

Referee: 2

Comments to the Author
(There are no comments.)

Referee: 3

Comments to the Author
Summary:

The submitted paper considers a timely scheduling problem, namely scheduling to improve the throughput and latency of large language model (LLM) inference systems. The problem is challenging due to two important details regarding how GPUs run LLM jobs. These are (a) jobs (or parts thereof) being served in parallel batches, with larger batch sizes yielding higher throughput; and (b) jobs using more memory the longer it runs (due to the KV cache), making the GPU's limited memory a significant constraint. These create a tension: (a) makes running larger batches more appealing, but (b) puts a limit on the possible batch sizes.

The paper makes the following technical contributions. First, a fluid model of the problem is studied to gain insight into what the "ideal case" for throughput looks like. Second, insights from the fluid model are applied to design scheduling algorithms for settings with stochastic arrivals (both known and unknown job service times). Third, these algorithms are theoretically analyzed to show that they do indeed approximately match the fluid model's idealized throughput. Fourth, the algorithms are compared to state-of-the-art schedulers and shown to improve throughput and latency.


High-level evaluation:

While there are aspects of the paper I found interesting, unfortunately, my overall opinion is that this paper does not rise to the level of OR. There are three main shortcomings:

(1) The paper makes several serious conceptual errors or oversights in its queueing theory. (a) The "heavy traffic" analysis involves not a heavy-traffic limit, but rather an infinite-horizon limit. (b) Some of the theoretical latency bounds follow immediately from positive recurrence of the Markov chain. (c) The paper derives complicated formulas for throughput, but because the system is open, the throughput has a much simpler formula and is the same under any stabilizing policy. (d) The simulations all take place in seemingly unstable systems without any comment about this instability, which is good for testing throughput but makes the latency measurements much less meaningful.

(2) The paper's contribution is not especially significant to the level of OR, especially in light of (1) above. (a) The core algorithmic idea is relatively simple and relatively clearly should improve throughput, but the more interesting question of how latency is affected is left without a strong answer. (b) A modeling choices about the memory constraint may side-step some key design difficulties.

(3) The paper's writing is sometimes unclear. (a) There are important things that are not adequately spelled out, e.g. the fluid models considered are never fully defined. (b) There is relatively little interpretation of the results, e.g. there is no interpretation at all for formulas for quantities derived in the fluid model. (c) Numerous typos and notation inconsistencies make the paper harder to read.

I give more details for (1) and (2) below, and I encourage the authors to do a careful editing pass to address (3).


Details for (1):

(a) As the paper itself states, the limit considered in Sections 4.2 and 4.3 (and the analogue in Section 5) is equivalent to scaling the time horizon up while keeping other parameters fixed. This means the limit is an infinite-horizon limit with the load fixed throughout. A heavy-traffic limit, in contrast, would see the load increase to the edge of the system's stability region. This said, a heavy-traffic limit is not the most appropriate tool for studying throughput in an open system (see (c) below).

(b) Given that all of the theoretical results in Section 4.3 (and analogues in Section 5) are really about infinite-horizon long-run averages, they are really statements about the recurrence of the Markov chain induced by the scheduling algorithm. With this in mind, many the results are unsurprising. Consider Theorem 1 as an example. In the second part, when the system is assumed "strictly stable", these results amount to saying that the Markov chain is positive recurrent, and that certain expectations over its stationary distribution are finite. Positive recurrence is not surprising, especially in light of the "pipeline" interpretation of the WAIT algorithm (see (2)(a) below), and finite expected latency is essentially universal in stable queues without heavy tails. While I admit that formally showing positive recurrance can sometimes be finicky, if it was difficult enough in this case to be an especially significant technical contribution, the core difficulties and key ideas that overcome them must be clearly explained in the main body of the paper.

(c) The system considered is an open system, with arrivals generated exogenously. Therefore, if the system is stable (more formally, if the induced Markov chain is positive recurrent), then the throughput of each job type is simply that job type's arrival rate, from which the throughput of response tokens can be easily computed. See e.g. the last line of equation (8), which can be obtained immediately; a similar simplification could have been applied to (4) earlier on. (By the way, the equation after (5) has a typo on the right-hand side, which I think should be consistent with (2).) So while the results for the fluid analysis are not wrong, they are presented unclearly. For example, the objective of "increasing throughput" might be better phrased as "increasing maximum throughput", or more precisely "maintaining stability throughout the entire stability region" (given the multidimensional nature). That is, in an open system, optimizing throughput is not about just one arrival rate, but rather the range of possible arrival rates (or vectors thereof) the policy can handle.

(d) All of the simulations in Section 6 appear to be in regimes where the systems are unstable, as visible from both types of plots. For the throughput plots, if the systems were stable, we would expect equal throughput (based on the arrival rate) for all stable systems. For the latency plots, later jobs experienced greater latency, implying buildup of the queues. Testing an unstable regime is appropriate for drawing out throughput differences (more precisely, maximum throughput / stability region differences, as discussed in (b) above). But it is not especially meaningful for latency: the first-order effect on latency in the unstable regime is how much the queue has built up, and so one simply expects better throughput to lead to better latency, as occurs in most cases shown in the paper. A more meaningful comparison would show, for example, infinite(-or-long-enough)-horizon mean latency as a function of arrival rate, which is a standard type of plot in queueing theory. (This would also show the stability region: policies with lower maximum throughput would have mean latency diverge to infinity at lower arrival rates.)


Details for (2):

(a) I believe the paper's algorithmic idea boils down to the following instance of "prevent pipeline bubbles". Ideally, in order to keep the memory usage of each job type constant, within a given type, we would have a constant number of jobs at each stage of progress. The WAIT algorithm essentially has a pipeline for each job type, and at each decision point, WAIT advances a given job type's pipeline (by including jobs of that type in the next service batch) if and only if there are enough not-yet-started jobs to keep the pipeline full (more than a given threshold at each stage). This is a nice idea, but it is not especially difficult to come up with, and it is not surprising that it increases the maximum possible throughput. So the interesting question is how much it affects latency, but as discussed in (1) above, the paper lacks strong theoretical or empirical latency results. And the fluid analysis to choose the thresholds used by WAIT essentially amounts to an exercise in Little's law and related formulas, so this too is not especially significant.

(b) The memory constraint seems to apply only to jobs in the batch currently being served (see Sections 2.3 and 2.4). But it is also stated that jobs can be preempted, and that their KV caches can be preserved if so. Is this a realistic model? At least as far as I understand, one would have to preserve the preempted jobs' KV caches at some other location (e.g. RAM or an SSD), and moving memory between the GPU and that other location would be time consuming. My first hunch is that the ideal resolution to this issue is to change the memory constraint to apply to all jobs, not just those in the current batch, and adapt the WAIT algorithm to obey this new constraint (if it does not coincidentally obey it already). Otherwise, the present model requires additional discussion or justification, e.g. perhaps there is data showing that the memory movement overhead is fast enough to be neglected.