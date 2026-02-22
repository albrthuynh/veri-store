# Project TODO: Distributed Object Store with Integrity

## 10-Week Timeline

### Week 1: Foundation & Setup

#### Mac (Security/Software Engineering)
- [X] Research homomorphic fingerprinting theory from paper
- [ ] Design security model: what attacks to defend against
- [X] Set up Python project structure with proper modules
- [X] Research SHA-256 and cryptographic primitives in Python

#### Albert (Systems/Backend)
- [ ] Research erasure coding fundamentals (Reed-Solomon)
- [ ] Design system architecture: client-server communication flow
- [ ] Set up HTTP server framework (Flask/FastAPI)
- [ ] Research `reedsolo` library or alternatives for erasure coding

#### Joint
- [X] Read and discuss paper sections 1-3 together
- [ ] Define API contract (PUT object, GET object, DELETE object)
- [X] Set up Git repository with proper .gitignore and README

---

### Week 2: Core Primitives

#### Mac (Security/Software Engineering)
- [X] Implement finite field arithmetic (F₂₅₆) primitivesimpleme
- [X] Implement irreducible polynomial generation for fingerprinting
- [X] Write unit tests for field operations
- [ ] Research random oracle implementation (deterministic r generation)

#### Albert (Systems/Backend)
- [ ] Implement basic erasure coding: encode function (data → 5 fragments)
- [ ] Implement decode function (any 3 fragments → original data)
- [ ] Write unit tests for encode/decode with various data sizes
- [ ] Handle edge cases: padding, empty data

#### Joint
- [ ] Code review each other's primitives
- [ ] Integration test: encode data, verify field arithmetic works on fragments

---

### Week 3: Fingerprinting Implementation

#### Mac (Security/Software Engineering)
- [ ] Implement division fingerprinting (Theorem 2.3)
- [ ] Implement `fp(r, d)` function: data → fingerprint
- [ ] Verify homomorphic properties (fp(r,d₁+d₂) = fp(r,d₁) + fp(r,d₂))
- [ ] Write comprehensive unit tests for fingerprinting

#### Albert (Systems/Backend)
- [ ] Design fingerprinted cross-checksum (fpcc) data structure
- [ ] Implement fpcc generation: hash all fragments, fingerprint first 3
- [ ] Implement random oracle for deterministic r: r = hash(all fragment hashes)
- [ ] Write serialization/deserialization for fpcc (JSON or pickle)

#### Joint
- [ ] Integration test: encode block → generate fpcc → verify it's correct
- [ ] Test homomorphic property on actual erasure-coded fragments

---

### Week 4: Server Infrastructure

#### Mac (Security/Software Engineering)
- [ ] Implement fragment verification logic on server side
- [ ] Given fragment dᵢ and fpcc, verify consistency (Definition 3.3)
- [ ] Handle verification failures gracefully (log errors, reject fragments)
- [ ] Write tests for Byzantine fault detection

#### Albert (Systems/Backend)
- [ ] Implement HTTP server process (Flask/FastAPI)
- [ ] Each server runs on different port (5001, 5002, ..., 5005)
- [ ] Implement storage backend (save fragments to disk with metadata)
- [ ] Implement server state management (track stored fragments)

#### Joint
- [ ] Test: start 5 servers, verify they respond to health checks
- [ ] Test: send fragment to server, verify it stores correctly

---

### Week 5: Client Implementation

#### Mac (Security/Software Engineering)
- [ ] Implement client-side security checks
- [ ] Verify server responses contain valid signatures
- [ ] Implement retry logic for failed requests
- [ ] Add logging for security events (verification failures)

#### Albert (Systems/Backend)
- [ ] Implement client HTTP requests (PUT, GET endpoints)
- [ ] Implement dispersal protocol: encode → compute fpcc → send to all servers
- [ ] Implement retrieval protocol: request from all → collect 3 → decode
- [ ] Handle network timeouts and server unavailability

#### Joint
- [ ] End-to-end test: client uploads object, 5 servers receive fragments
- [ ] Test retrieval: client fetches object successfully

---

### Week 6: Fault Tolerance

#### Mac (Security/Software Engineering)
- [ ] Implement Byzantine fault injection (server sends wrong fragment)
- [ ] Test detection: client should reject inconsistent fragments
- [ ] Measure false positive rate (valid fragments incorrectly rejected)
- [ ] Document security guarantees achieved

#### Albert (Systems/Backend)
- [ ] Implement crash fault simulation (kill servers mid-operation)
- [ ] Test retrieval with only 3/5 servers available
- [ ] Implement graceful degradation (continue with failures)
- [ ] Add metrics: success rate, fragments lost, recovery time

#### Joint
- [ ] Integration test: upload with 5 servers, retrieve with only 3
- [ ] Test Byzantine detection: inject bad fragment, verify rejection
- [ ] Test: 2 servers crash, system still works (3 remain)

---

### Week 7: HTTP API Refinement

#### Mac (Security/Software Engineering)
- [ ] Implement authentication/authorization (optional: simple token-based)
- [ ] Add request validation (check payload structure)
- [ ] Implement rate limiting per client
- [ ] Add security headers to HTTP responses

#### Albert (Systems/Backend)
- [ ] Implement proper HTTP status codes (200, 404, 500, etc.)
- [ ] Add error messages in responses (JSON error objects)
- [ ] Implement idempotency for PUT requests
- [ ] Add request/response logging

#### Joint
- [ ] API documentation: document all endpoints with examples
- [ ] Test with curl/Postman: verify API works as expected
- [ ] Load testing: can system handle 100 concurrent requests?

---

### Week 8: Testing & Validation

#### Mac (Security/Software Engineering)
- [ ] Write comprehensive security test suite
- [ ] Test collision probability empirically (try to find collisions)
- [ ] Penetration testing: try to break integrity guarantees
- [ ] Verify Theorem 3.4 bound holds empirically

#### Albert (Systems/Backend)
- [ ] Write integration tests for full workflows
- [ ] Test edge cases: empty files, 100MB files, binary data
- [ ] Test concurrent clients accessing same object
- [ ] Performance testing: measure throughput (objects/sec)

#### Joint
- [ ] Bug fixing week: address all discovered issues
- [ ] Code cleanup: remove dead code, improve documentation
- [ ] Refactor: improve code quality based on learnings

---

### Week 9: Performance & Documentation

#### Mac (Security/Software Engineering)
- [ ] Measure bandwidth overhead vs. replication
- [ ] Measure verification time per fragment
- [ ] Create security analysis document
- [ ] Prepare demo: show Byzantine fault detection

#### Albert (Systems/Backend)
- [ ] Measure end-to-end latency (PUT and GET)
- [ ] Profile code: find bottlenecks (erasure coding? network?)
- [ ] Optimize hot paths if possible
- [ ] Create architecture diagram and system documentation

#### Joint
- [ ] Write final report: introduction, implementation, evaluation
- [ ] Create performance graphs (latency, throughput, overhead)
- [ ] Prepare presentation slides

---

### Week 10: Demo Preparation & Final Touches

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
- **Week 4:** ✅ Basic client-server communication functional
- **Week 6:** ✅ Fault tolerance demonstrated (crashes + Byzantine)
- **Week 8:** ✅ All testing complete, system stable
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
- [ ] HTTP client (PUT/GET/DELETE)
- [ ] Verification logic
- [ ] Test suite (unit + integration)

### Documentation
- [ ] README with setup instructions
- [ ] API documentation
- [ ] Architecture diagram
- [ ] Final report (10-15 pages)

### Demo Requirements
- [ ] Normal operation: upload → retrieve
- [ ] Fault tolerance: crash 2 servers → still works
- [ ] Byzantine detection: inject bad fragment → rejected
- [ ] Performance metrics visualization

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
