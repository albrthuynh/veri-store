# Project TODO: Distributed Object Store with Integrity

## 10-Week Timeline

### Week 1: Foundation & Setup (M 2/9-F 2/13)

#### Mac (Security/Software Engineering)

- [x] Research homomorphic fingerprinting theory from paper
- [x] Design security model: what attacks to defend against
- [x] Set up Python project structure with proper modules
- [x] Research SHA-256 and cryptographic primitives in Python

#### Albert (Systems/Backend)

- [x] Research erasure coding fundamentals (Reed-Solomon)
- [x] Design system architecture: client-server communication flow
- [x] Set up HTTP server framework (Flask/FastAPI)
- [x] Research `reedsolo` library or alternatives for erasure coding

#### Joint

- [x] Read and discuss paper sections 1-3 together
- [x] Define API contract (PUT object, GET object, DELETE object)
- [x] Set up Git repository with proper .gitignore and README

---

### Week 2: Core Primitives (M 2/16-F 2/20)

#### Mac (Security/Software Engineering)

- [x] Implement finite field arithmetic (F₂₅₆) primitives
- [x] Implement irreducible polynomial generation for fingerprinting
- [x] Write unit tests for field operations
- [x] Research random oracle implementation (deterministic r generation)

#### Albert (Systems/Backend)

- [x] Implement basic erasure coding: encode function (data → 5 fragments)
- [x] Implement decode function (any 3 fragments → original data)
- [x] Write unit tests for encode/decode with various data sizes
- [x] Handle edge cases: padding, empty data

#### Joint

- [x] Code review each other's primitives
- [x] Integration test: encode data, verify field arithmetic works on fragments

---

### Week 3: Fingerprinting Implementation (M 2/23-F 2/27)

#### Mac (Security/Software Engineering)

- [X] Implement division fingerprinting (Theorem 2.3)
- [X] Implement `fp(r, d)` function: data → fingerprint
- [X] Verify homomorphic properties (fp(r,d₁+d₂) = fp(r,d₁) + fp(r,d₂))
- [X] Write comprehensive unit tests for fingerprinting

#### Albert (Systems/Backend)

- [x] Design fingerprinted cross-checksum (fpcc) data structure
- [x] Implement fpcc generation: hash all fragments, fingerprint first 3
- [x] Implement random oracle for deterministic r: r = hash(all fragment hashes)
- [x] Write serialization/deserialization for fpcc (JSON or pickle)

#### Joint

- [x] Integration test: encode block → generate fpcc → verify it's correct
- [x] Test homomorphic property on actual erasure-coded fragments

---

### Week 4: Server Infrastructure (M 3/2-F 3/6)

#### Mac (Security/Software Engineering)

- [X] Implement fragment verification logic on server side
- [X] Given fragment dᵢ and fpcc, verify consistency (Definition 3.3)
- [X] Handle verification failures gracefully (log errors, reject fragments)
- [X] Write tests for Byzantine fault detection
- [X] **Security Model §4.1:** External Libraries — documented
- [X] **Security Model §1.1:** Write Document Purpose
- [X] **Security Model §1.2:** Write System Overview
- [X] **Security Model §3.1:** Write Primary Use Case
- [X] **Security Model §3.2:** Write Anti-Scenarios
- [X] **Security Model §6.2:** Write Authenticated Client trust level
- [X] **Security Model §6.4:** Write Untrusted Network trust level

#### Albert (Systems/Backend)

- [x] Implement HTTP server process (Flask/FastAPI)
- [x] Each server runs on different port (5001, 5002, ..., 5005)
- [x] Implement storage backend (save fragments to disk with metadata)
- [x] Implement server state management (track stored fragments)
- [x] **Security Model §5:** Implementation Assumptions — documented
- [x] **Security Model §6.1:** Administrator trust level — documented
- [x] **Security Model §2.1:** Write In Scope
- [x] **Security Model §2.2:** Write Out of Scope
- [x] **Security Model §4.2:** Write System Dependencies
- [x] **Security Model §6.3:** Write Storage Server trust level
- [x] **Security Model §7.1:** Write Client API entry points (store, retrieve, verify)
- [x] **Security Model §7.2:** Write Inter-Server Communication entry points
- [x] **Security Model §7.3:** Write Storage Subsystem entry points

#### Joint

- [x] Test: start 5 servers, verify they respond to health checks
- [x] Test: send fragment to server, verify it stores correctly
- [x] **Security Model:** Review and sign off on §1–7 together

---

### Week 5: Client Implementation (M 3/9-F 3/13)

#### Mac (Security/Software Engineering)

- [X] Implement client-side security checks
- [X] Verify server responses contain valid signatures
- [ ] Implement retry logic for failed requests
- [ ] Add logging for security events (verification failures)
- [ ] **Security Model §8.1:** Write Data Blocks protected asset
- [ ] **Security Model §8.2:** Write Erasure-Coded Fragments protected asset
- [ ] **Security Model §8.3:** Write Homomorphic Fingerprints protected asset
- [ ] **Security Model §8.4:** Write System Resources protected asset

#### Albert (Systems/Backend)

- [x] Implement client HTTP requests (PUT, GET endpoints)
- [x] Implement dispersal protocol: encode → compute fpcc → send to all servers
- [x] Implement retrieval protocol: request from all → collect 3 → decode
- [x] Handle network timeouts and server unavailability
- [x] **Security Model §9.1.1:** Write Client DFD component description
- [x] **Security Model §9.1.2–9.1.4:** Write Encode Block, Compute Fingerprint, Distribute Fragments descriptions
- [x] **Security Model §9.1.5–9.1.8:** Write Network, Fragment Storage, Verify Fragments, Reconstruct Block descriptions

#### Joint

- [x] End-to-end test: client uploads object, 5 servers receive fragments
- [x] Test retrieval: client fetches object successfully
- [ ] **Security Model:** Review §8 and §9.1 together; verify DFD matches implementation

---

### Week 6: Fault Tolerance (M 3/16-F 3/20)

#### Mac (Security/Software Engineering)

- [ ] Implement Byzantine fault injection (server sends wrong fragment)
- [ ] Test detection: client should reject inconsistent fragments
- [ ] Measure false positive rate (valid fragments incorrectly rejected)
- [ ] Document security guarantees achieved
- [ ] **Security Model §10.1:** Write Spoofing threats (S.1, S.2, S.3)
- [ ] **Security Model §10.2:** Write Tampering threats (T.1, T.2, T.3, T.4)

#### Albert (Systems/Backend)

- [x] Implement crash fault simulation (kill servers mid-operation)
- [x] Test retrieval with only 3/5 servers available
- [x] Implement graceful degradation (continue with failures)
- [x] Add metrics: success rate, fragments lost, recovery time
- [x] **Security Model §10.3:** Write Repudiation threats (R.1, R.2, R.3)
- [x] **Security Model §10.4:** Write Information Disclosure threats (I.1, I.2, I.3, I.4)

#### Joint

- [ ] Integration test: upload with 5 servers, retrieve with only 3
- [ ] Test Byzantine detection: inject bad fragment, verify rejection
- [ ] Test: 2 servers crash, system still works (3 remain)
- [ ] **Security Model §10.5:** Write Denial of Service threats (D.1, D.2, D.3, D.4)
- [ ] **Security Model §10.6:** Write Elevation of Privilege threats (E.1, E.2, E.3, E.4)
- [ ] **Security Model:** Review complete §10 STRIDE analysis together

---

### Week 7: HTTP API Refinement (M 3/23-F 3/27) [SPRING BREAK]

#### Mac (Security/Software Engineering)

- [ ] Implement authentication/authorization (optional: simple token-based)
- [ ] Add request validation (check payload structure)
- [ ] Implement rate limiting per client
- [ ] Add security headers to HTTP responses
- [ ] **Security Model §11.1:** Write Spoofing threat resolutions (S.1, S.2, S.3)
- [ ] **Security Model §11.2:** Write Tampering threat resolutions (T.1, T.2, T.3, T.4)

#### Albert (Systems/Backend)

- [ ] Implement proper HTTP status codes (200, 404, 500, etc.)
- [ ] Add error messages in responses (JSON error objects)
- [ ] Implement idempotency for PUT requests
- [ ] Add request/response logging
- [ ] **Security Model §11.3:** Write Repudiation threat resolutions (R.1, R.2, R.3)
- [ ] **Security Model §11.4:** Write Information Disclosure threat resolutions (I.1, I.2, I.3, I.4)

#### Joint

- [ ] API documentation: document all endpoints with examples
- [ ] Test with curl/Postman: verify API works as expected
- [ ] Load testing: can system handle 100 concurrent requests?
- [ ] **Security Model §11.5:** Write Denial of Service resolutions (D.1, D.2, D.3, D.4)
- [ ] **Security Model §11.6:** Write Elevation of Privilege resolutions (E.1, E.2, E.3, E.4)
- [ ] **Security Model:** Review complete §11 together; verify all resolutions match implementation

---

### Week 8: Testing & Validation (M 3/30-F 4/3)

#### Mac (Security/Software Engineering)

- [ ] Write comprehensive security test suite
- [ ] Test collision probability empirically (try to find collisions)
- [ ] Penetration testing: try to break integrity guarantees
- [ ] Verify Theorem 3.4 bound holds empirically
- [ ] **Security Model §12.2:** Write Known Limitations
- [ ] **Security Model §12.3:** Write Integration Considerations
- [ ] **Security Model §13.1:** Write Security Test Suite

#### Albert (Systems/Backend)

- [ ] Write integration tests for full workflows
- [ ] Test edge cases: empty files, 100MB files, binary data
- [ ] Test concurrent clients accessing same object
- [ ] Performance testing: measure throughput (objects/sec)
- [ ] **Security Model §12.1:** Write Deployment Recommendations
- [ ] **Security Model §13.2:** Write Code Review Process
- [ ] **Security Model §13.3:** Write Regression Testing

#### Joint

- [ ] Bug fixing week: address all discovered issues
- [ ] Code cleanup: remove dead code, improve documentation
- [ ] Refactor: improve code quality based on learnings
- [ ] **Security Model:** Review §12 and §13 together

---

### Week 9: Performance & Documentation (M 4/6-F 4/10)

#### Mac (Security/Software Engineering)

- [ ] Measure bandwidth overhead vs. replication
- [ ] Measure verification time per fragment
- [ ] Create security analysis document
- [ ] Prepare demo: show Byzantine fault detection
- [ ] **Security Model:** Final proofreading pass — Mac sections (§1, §3, §4.1, §6.2, §6.4, §8, §10.1, §10.2, §11.1, §11.2, §12.2, §12.3, §13.1)
- [ ] **Security Model:** Ensure all threat resolutions reference actual implementation (file/function names where possible)

#### Albert (Systems/Backend)

- [ ] Measure end-to-end latency (PUT and GET)
- [ ] Profile code: find bottlenecks (erasure coding? network?)
- [ ] Optimize hot paths if possible
- [ ] Create architecture diagram and system documentation
- [ ] **Security Model §14.1:** Write Review Schedule
- [ ] **Security Model §14.2:** Write Change Process
- [ ] **Security Model:** Final proofreading pass — Albert sections (§2, §4.2, §5, §6.1, §6.3, §7, §9.1, §10.3, §10.4, §11.3, §11.4, §12.1, §13.2, §13.3)

#### Joint

- [ ] Write final report: introduction, implementation, evaluation
- [ ] Create performance graphs (latency, throughput, overhead)
- [ ] Prepare presentation slides
- [ ] **Security Model §14.3:** Write Version History entry; bump document to v1.0
- [ ] **Security Model:** Final joint sign-off; commit to main branch

---

### Week 10: Demo Preparation & Final Touches (M 4/13-F 4/17)

#### Mac (Security/Software Engineering)

- [ ] Prepare security demo: inject malicious fragment, show detection
- [ ] Create attack scenarios for presentation
- [ ] Polish logging output for demo (make it visual/clear)
- [ ] Rehearse security explanation for Q&A

#### Albert (Systems/Backend)

- [ ] Prepare fault tolerance demo: kill servers, show recovery
- [ ] Create simple CLI tool for demo (easier than curl)
- [ ] Ensure demo runs smoothly on presentation laptop
- [ ] Prepare architecture walkthrough

#### Joint

- [ ] Full presentation rehearsal (20-30 minutes)
- [ ] Prepare for Q&A: anticipate questions about design choices
- [ ] Final code cleanup and README polish
- [ ] Submit final report and code

---

## Key Milestones

- **Week 2:** ✅ Core primitives working (erasure coding + fingerprinting)
- **Week 4:** ✅ Basic client-server communication functional; §1–7 security model drafted
- **Week 6:** ✅ Fault tolerance demonstrated (crashes + Byzantine); §10 STRIDE analysis complete
- **Week 7:** ✅ §11 threat resolutions complete
- **Week 8:** ✅ All testing complete, system stable; §12–13 complete
- **Week 9:** ✅ Security model v1.0 complete and signed off
- **Week 10:** ✅ Presentation ready, report submitted

---

## Weekly Sync Schedule

**Monday:** Planning meeting (30 min)

- Review last week's progress
- Plan current week's tasks
- Identify blockers

**Thursday:** Progress check (30 min)

- Demo what's working
- Discuss technical challenges
- Adjust plans if needed

**Sunday:** Code review (1 hour)

- Review each other's code
- Merge to main branch
- Update TODO.md checkboxes

---

## Final Deliverables Checklist

### Code Components

- [ ] Erasure coding (encode/decode)
- [ ] Homomorphic fingerprinting
- [ ] Fingerprinted cross-checksum
- [ ] 5 HTTP servers (can run as processes)
- [x] HTTP client (PUT/GET/DELETE)
- [ ] Verification logic
- [ ] Test suite (unit + integration)

### Documentation

- [ ] README with setup instructions
- [ ] API documentation
- [ ] Architecture diagram
- [ ] Final report (10-15 pages)
- [ ] Security model v1.0 (fully populated, all §1–14 complete)

### Demo Requirements

- [x] Normal operation: upload → retrieve
- [ ] Fault tolerance: crash 2 servers → still works
- [ ] Byzantine detection: inject bad fragment → rejected
- [ ] Performance metrics visualization

---

## Security Model Section Ownership

| Section | Owner | Target Week |
|---------|-------|-------------|
| §1.1 Document Purpose | Mac | Week 4 |
| §1.2 System Overview | Mac | Week 4 |
| §2.1 In Scope | Albert | Week 4 |
| §2.2 Out of Scope | Albert | Week 4 |
| §3.1 Primary Use Case | Mac | Week 4 |
| §3.2 Anti-Scenarios | Mac | Week 4 |
| §4.1 External Libraries | Mac | ✅ Done |
| §4.2 System Dependencies | Albert | Week 4 |
| §5 Implementation Assumptions | Albert | ✅ Done |
| §6.1 Administrator | Albert | ✅ Done |
| §6.2 Authenticated Client | Mac | Week 4 |
| §6.3 Storage Server | Albert | Week 4 |
| §6.4 Untrusted Network | Mac | Week 4 |
| §7.1 Client API | Albert | Week 4 |
| §7.2 Inter-Server Communication | Albert | Week 4 |
| §7.3 Storage Subsystem | Albert | Week 4 |
| §8.1 Data Blocks | Mac | Week 5 |
| §8.2 Erasure-Coded Fragments | Mac | Week 5 |
| §8.3 Homomorphic Fingerprints | Mac | Week 5 |
| §8.4 System Resources | Mac | Week 5 |
| §9.1 DFD Component Descriptions | Albert | Week 5 |
| §10.1 Spoofing | Mac | Week 6 |
| §10.2 Tampering | Mac | Week 6 |
| §10.3 Repudiation | Albert | Week 6 |
| §10.4 Information Disclosure | Albert | Week 6 |
| §10.5 Denial of Service | Joint | Week 6 |
| §10.6 Elevation of Privilege | Joint | Week 6 |
| §11.1 Spoofing Resolutions | Mac | Week 7 |
| §11.2 Tampering Resolutions | Mac | Week 7 |
| §11.3 Repudiation Resolutions | Albert | Week 7 |
| §11.4 Information Disclosure Resolutions | Albert | Week 7 |
| §11.5 DoS Resolutions | Joint | Week 7 |
| §11.6 Elevation of Privilege Resolutions | Joint | Week 7 |
| §12.1 Deployment Recommendations | Albert | Week 8 |
| §12.2 Known Limitations | Mac | Week 8 |
| §12.3 Integration Considerations | Mac | Week 8 |
| §13.1 Security Test Suite | Mac | Week 8 |
| §13.2 Code Review Process | Albert | Week 8 |
| §13.3 Regression Testing | Albert | Week 8 |
| §14.1 Review Schedule | Albert | Week 9 |
| §14.2 Change Process | Albert | Week 9 |
| §14.3 Version History | Joint | Week 9 |

---

## Notes

- **Paper Reference:** "Verifying Distributed Erasure-Coded Data" by Hendricks, Ganger, and Reiter (PODC 2007)
- **Erasure Coding:** 3-of-5 scheme (any 3 fragments reconstruct original)
- **Security:** Homomorphic fingerprints ensure fragment consistency
- **Infrastructure:** Python processes on localhost (ports 5001-5005)
- **Protocol:** HTTP/REST API

---

## Useful Commands

```bash
# Start all servers
python server.py --port 5001 --id 1 &
python server.py --port 5002 --id 2 &
python server.py --port 5003 --id 3 &
python server.py --port 5004 --id 4 &
python server.py --port 5005 --id 5 &

# Run client
python client.py put myfile.txt
python client.py get myfile.txt

# Run tests
pytest tests/

# Kill all servers
pkill -f server.py
```

---

## Resources

- Paper: https://dl.acm.org/doi/10.1145/1281100.1281122
- Reed-Solomon: https://pypi.org/project/reedsolo/
- Flask: https://flask.palletsprojects.com/
- FastAPI: https://fastapi.tiangolo.com/
