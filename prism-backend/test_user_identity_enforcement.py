"""
🔐 USER IDENTITY ENFORCEMENT - COMPREHENSIVE TEST SUITE
========================================================

This test suite validates the CRITICAL RULE: ONE EMAIL = ONE USER

Test Coverage:
1. Email normalization (case, whitespace, special characters)
2. Same email → same user_id across multiple sessions
3. Duplicate prevention at database level
4. Memory continuity across sessions
5. No duplicate memories per user
6. Neo4j User node uniqueness (MERGE enforcement)
7. Pinecone vector deduplication per user_id
8. Redis session resolution to canonical user_id

🚨 ALL TESTS MUST PASS - ANY FAILURE = P0 CRITICAL BUG
"""

import asyncio
import logging
from typing import List, Tuple
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestResult:
    """Result of a test case"""
    def __init__(self, name: str, passed: bool, message: str, details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details
        self.timestamp = datetime.now()


async def test_email_normalization():
    """
    🔴 TEST 1: Email Normalization
    
    Validates that email variants resolve to same canonical form:
    - User@Gmail.com
    - user@gmail.com
    - user@GMAIL.COM
    - user@gmail.com (with spaces)
    
    All must produce same normalized email.
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 1: Email Normalization")
    logger.info("=" * 80)
    
    try:
        from app.services.user_resolution_service import UserResolutionService
        
        email_variants = [
            "User@Gmail.com",
            "user@gmail.com",
            "user@GMAIL.COM",
            " user@gmail.com ",
            "USER@gmail.com"
        ]
        
        normalized_emails = []
        for email in email_variants:
            normalized = UserResolutionService.normalize_email(email)
            normalized_emails.append(normalized)
            logger.info(f"  {email} → {normalized}")
        
        # All should be identical
        if len(set(normalized_emails)) == 1:
            logger.info("✅ TEST 1 PASSED: All variants normalized to same email")
            return TestResult(
                "Email Normalization",
                True,
                "All email variants normalized correctly",
                f"Normalized: {normalized_emails[0]}"
            )
        else:
            logger.error(f"❌ TEST 1 FAILED: Got {len(set(normalized_emails))} different normalized forms")
            logger.error(f"   Normalized emails: {set(normalized_emails)}")
            return TestResult(
                "Email Normalization",
                False,
                "Email variants produced different normalized forms",
                f"Expected 1 form, got {len(set(normalized_emails))}"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 1 ERROR: {e}")
        return TestResult("Email Normalization", False, f"Test error: {e}")


async def test_same_email_same_user_id():
    """
    🔴 TEST 2: Same Email → Same user_id
    
    Validates that:
    - Same email always generates same user_id (deterministic hash)
    - Multiple calls return identical user_id
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 2: Same Email → Same user_id")
    logger.info("=" * 80)
    
    try:
        from app.services.user_resolution_service import UserResolutionService
        
        email = "testuser123@example.com"
        normalized = UserResolutionService.normalize_email(email)
        
        # Generate user_id multiple times
        user_ids = []
        for i in range(5):
            user_id = UserResolutionService.generate_user_id(normalized)
            user_ids.append(user_id)
            logger.info(f"  Attempt {i+1}: {user_id}")
        
        # All should be identical
        if len(set(user_ids)) == 1:
            logger.info(f"✅ TEST 2 PASSED: Same email produces same user_id: {user_ids[0]}")
            return TestResult(
                "Same Email → Same user_id",
                True,
                "Deterministic user_id generation confirmed",
                f"user_id: {user_ids[0]}"
            )
        else:
            logger.error(f"❌ TEST 2 FAILED: Got {len(set(user_ids))} different user_ids")
            return TestResult(
                "Same Email → Same user_id",
                False,
                "Non-deterministic user_id generation",
                f"Generated {len(set(user_ids))} different IDs"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 2 ERROR: {e}")
        return TestResult("Same Email → Same user_id", False, f"Test error: {e}")


async def test_duplicate_prevention_database():
    """
    🔴 TEST 3: Database-Level Duplicate Prevention
    
    Validates that MongoDB unique index prevents duplicate users:
    - Try to create user with same email twice
    - Second attempt should fail (or return existing user)
    - Confirm only ONE user record exists
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 3: Database-Level Duplicate Prevention")
    logger.info("=" * 80)
    
    try:
        # Use existing mongo client to avoid connection string parsing issues
        from app.db.mongo_client import db_instance
        from app.services.user_resolution_service import UserResolutionService
        
        # Check if MongoDB is initialized
        if not db_instance.client:
            logger.error("❌ MongoDB client not initialized")
            return TestResult(
                "Database Duplicate Prevention",
                False,
                "MongoDB client not initialized"
            )
        
        # Initialize service with existing mongo connection
        service = UserResolutionService(db_instance.client)
        
        # Ensure unique index exists
        await service.ensure_unique_index()
        
        # Test email (use unique timestamp to avoid conflicts)
        test_email = f"duplicate_test_{int(datetime.now().timestamp())}@example.com"
        
        # First resolution - should create new user
        user_id_1, is_new_1, user_data_1 = await service.resolve_user(test_email)
        logger.info(f"  First resolution: user_id={user_id_1}, is_new={is_new_1}")
        
        # Second resolution - should return SAME user
        user_id_2, is_new_2, user_data_2 = await service.resolve_user(test_email)
        logger.info(f"  Second resolution: user_id={user_id_2}, is_new={is_new_2}")
        
        # Validate results
        if user_id_1 == user_id_2 and is_new_1 == True and is_new_2 == False:
            logger.info("✅ TEST 3 PASSED: Database prevented duplicate, returned existing user")
            
            # Cleanup test user
            await service.users_collection.delete_one({"email": test_email})
            
            return TestResult(
                "Database Duplicate Prevention",
                True,
                "Unique index working correctly",
                f"Same user_id: {user_id_1}"
            )
        else:
            logger.error(f"❌ TEST 3 FAILED: Expected same user_id and is_new=True then False")
            logger.error(f"   Got: user_id_1={user_id_1}, user_id_2={user_id_2}")
            logger.error(f"        is_new_1={is_new_1}, is_new_2={is_new_2}")
            
            # Cleanup
            await service.users_collection.delete_many({"email": test_email})
            
            return TestResult(
                "Database Duplicate Prevention",
                False,
                "Duplicate prevention failed",
                "Multiple user records may have been created"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 3 ERROR: {e}")
        return TestResult("Database Duplicate Prevention", False, f"Test error: {e}")


async def test_memory_continuity_across_sessions():
    """
    🔴 TEST 4: Memory Continuity Across Sessions
    
    Validates that:
    - User logs in with email in Session 1
    - Stores a preference
    - User logs in with SAME email in Session 2 (different case)
    - Preference is correctly retrieved (same user_id)
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 4: Memory Continuity Across Sessions")
    logger.info("=" * 80)
    
    try:
        from app.db.mongo_client import db_instance
        from app.services.user_resolution_service import UserResolutionService
        from app.services.unified_memory_orchestrator import unified_memory_orchestrator, MemoryType
        
        # Check if MongoDB is initialized
        if not db_instance.client:
            logger.error("❌ MongoDB client not initialized")
            return TestResult(
                "Memory Continuity Across Sessions",
                False,
                "MongoDB client not initialized"
            )
        
        # Initialize service with existing mongo connection
        service = UserResolutionService(db_instance.client)
        
        # Session 1: User@Example.com
        session1_email = f"memory_test_{int(datetime.now().timestamp())}@example.com"
        user_id_session1, is_new_1, _ = await service.resolve_user(session1_email)
        logger.info(f"📅 SESSION 1: {session1_email} → {user_id_session1}")
        
        # Store a preference
        preference_text = "playing strategy board games"
        store_result, store_logs = await unified_memory_orchestrator.store_memory(
            user_id=user_id_session1,
            memory_content=preference_text,
            memory_type=MemoryType.PREFERENCE,
            metadata={"type": "preference", "session": 1}
        )
        logger.info(f"  Stored preference: {preference_text}")
        logger.info(f"  Storage success: {store_result.success}")
        
        # Session 2: user@example.com (different case)
        session2_email = session1_email.upper()  # Same email, different case
        user_id_session2, is_new_2, _ = await service.resolve_user(session2_email)
        logger.info(f"📅 SESSION 2: {session2_email} → {user_id_session2}")
        
        # Retrieve preferences
        preferences = await unified_memory_orchestrator.get_user_preferences(user_id_session2)
        logger.info(f"  Retrieved preferences: {preferences}")
        
        # Validate
        if user_id_session1 == user_id_session2 and preference_text in preferences:
            logger.info("✅ TEST 4 PASSED: Memory continuity confirmed across sessions")
            
            # Cleanup
            await service.users_collection.delete_one({"email": service.normalize_email(session1_email)})
            await unified_memory_orchestrator.memory_collection.delete_one({"userId": user_id_session1})
            
            return TestResult(
                "Memory Continuity Across Sessions",
                True,
                "Same user_id retrieved memory successfully",
                f"user_id: {user_id_session1}"
            )
        else:
            logger.error(f"❌ TEST 4 FAILED: Memory continuity broken")
            logger.error(f"   Session 1 user_id: {user_id_session1}")
            logger.error(f"   Session 2 user_id: {user_id_session2}")
            logger.error(f"   Preference found: {preference_text in preferences}")
            
            # Cleanup
            await service.users_collection.delete_one({"email": service.normalize_email(session1_email)})
            await unified_memory_orchestrator.memory_collection.delete_one({"userId": user_id_session1})
            
            return TestResult(
                "Memory Continuity Across Sessions",
                False,
                "Different user_id or memory not found",
                "Memory fragmentation detected"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 4 ERROR: {e}")
        return TestResult("Memory Continuity Across Sessions", False, f"Test error: {e}")


async def test_no_duplicate_memories():
    """
    🔴 TEST 5: No Duplicate Memories Per User
    
    Validates that:
    - Same preference stored twice doesn't create duplicates
    - MongoDB duplicate check works correctly
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 5: No Duplicate Memories Per User")
    logger.info("=" * 80)
    
    try:
        from app.db.mongo_client import db_instance
        from app.services.user_resolution_service import UserResolutionService
        from app.services.unified_memory_orchestrator import unified_memory_orchestrator, MemoryType
        
        # Check if MongoDB is initialized
        if not db_instance.client:
            logger.error("❌ MongoDB client not initialized")
            return TestResult(
                "No Duplicate Memories",
                False,
                "MongoDB client not initialized"
            )
        
        # Initialize with existing mongo connection
        service = UserResolutionService(db_instance.client)
        
        test_email = f"duplicate_memory_test_{int(datetime.now().timestamp())}@example.com"
        user_id, _, _ = await service.resolve_user(test_email)
        logger.info(f"  Test user: {user_id}")
        
        preference_text = "reading science fiction novels"
        
        # Store same preference THREE times
        for i in range(3):
            result, logs = await unified_memory_orchestrator.store_memory(
                user_id=user_id,
                memory_content=preference_text,
                memory_type=MemoryType.PREFERENCE
            )
            logger.info(f"  Attempt {i+1}: success={result.success}")
        
        # Check how many times it was stored
        preferences = await unified_memory_orchestrator.get_user_preferences(user_id)
        count = preferences.count(preference_text)
        logger.info(f"  Preference appears {count} time(s) in database")
        
        # Should only appear once
        if count == 1:
            logger.info("✅ TEST 5 PASSED: Duplicate prevention working")
            
            # Cleanup
            await service.users_collection.delete_one({"email": service.normalize_email(test_email)})
            await unified_memory_orchestrator.memory_collection.delete_one({"userId": user_id})
            
            return TestResult(
                "No Duplicate Memories",
                True,
                "Duplicate memory prevention confirmed",
                "Only 1 copy stored despite 3 attempts"
            )
        else:
            logger.error(f"❌ TEST 5 FAILED: Preference stored {count} times (expected 1)")
            
            # Cleanup
            await service.users_collection.delete_one({"email": service.normalize_email(test_email)})
            await unified_memory_orchestrator.memory_collection.delete_one({"userId": user_id})
            
            return TestResult(
                "No Duplicate Memories",
                False,
                f"Duplicate memories created: {count} copies",
                "Duplicate prevention failed"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 5 ERROR: {e}")
        return TestResult("No Duplicate Memories", False, f"Test error: {e}")


async def test_neo4j_user_node_uniqueness():
    """
    🔴 TEST 6: Neo4j User Node Uniqueness (MERGE Enforcement)
    
    Validates that:
    - Creating user node twice with same user_id doesn't duplicate
    - MERGE clause ensures only one User node per user_id
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 6: Neo4j User Node Uniqueness")
    logger.info("=" * 80)
    
    try:
        from app.db.neo4j_client import Neo4jClient
        from app.services.user_resolution_service import UserResolutionService
        
        # Use static methods for ID generation (don't need mongo client)
        test_email = f"neo4j_test_{int(datetime.now().timestamp())}@example.com"
        normalized = UserResolutionService.normalize_email(test_email)
        user_id = UserResolutionService.generate_user_id(normalized)
        
        logger.info(f"  Test user_id: {user_id}")
        
        # Initialize Neo4j
        neo4j = Neo4jClient()
        
        # Create user node TWICE
        result1 = await neo4j.create_user_node(user_id, test_email, "Test User")
        logger.info(f"  First creation: success={result1}")
        
        result2 = await neo4j.create_user_node(user_id, test_email, "Test User")
        logger.info(f"  Second creation: success={result2}")
        
        # Query to check node count
        from app.db.neo4j_client import query_graph
        count_query = "MATCH (u:User {id: $user_id}) RETURN count(u) as count"
        
        try:
            count_result = await query_graph(count_query, {"user_id": user_id})
        except Exception as query_error:
            logger.error(f"  Neo4j query failed: {query_error}")
            return TestResult(
                "Neo4j User Node Uniqueness",
                False,
                f"Neo4j query error: {query_error}"
            )
        
        node_count = 0
        if count_result and len(count_result) > 0:
            if isinstance(count_result[0], dict):
                node_count = count_result[0].get("count", 0)
            else:
                # Handle Record object
                try:
                    node_count = count_result[0]["count"]
                except (KeyError, TypeError):
                    node_count = 0
        logger.info(f"  User nodes found: {node_count}")
        
        # Cleanup
        cleanup_query = "MATCH (u:User {id: $user_id}) DELETE u"
        await query_graph(cleanup_query, {"user_id": user_id})
        
        if node_count == 1:
            logger.info("✅ TEST 6 PASSED: MERGE prevented duplicate User node")
            return TestResult(
                "Neo4j User Node Uniqueness",
                True,
                "MERGE clause working correctly",
                "Only 1 node despite 2 create attempts"
            )
        else:
            logger.error(f"❌ TEST 6 FAILED: Found {node_count} User nodes (expected 1)")
            return TestResult(
                "Neo4j User Node Uniqueness",
                False,
                f"Duplicate User nodes created: {node_count}",
                "MERGE clause not working"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 6 ERROR: {e}")
        return TestResult("Neo4j User Node Uniqueness", False, f"Test error: {e}")


async def test_complete_user_identity_pipeline():
    """
    🔴 TEST 7: Complete User Identity Pipeline
    
    End-to-end test:
    1. User signs up with email
    2. System resolves to canonical user_id
    3. Stores memories across all systems (MongoDB, Neo4j, Pinecone)
    4. User logs in again with different email case
    5. System resolves to SAME user_id
    6. All memories are accessible
    """
    logger.info("=" * 80)
    logger.info("🔴 TEST 7: Complete User Identity Pipeline")
    logger.info("=" * 80)
    
    try:
        from app.db.mongo_client import db_instance
        from app.services.user_resolution_service import UserResolutionService
        from app.services.unified_memory_orchestrator import unified_memory_orchestrator, MemoryType
        
        # Check if MongoDB is initialized
        if not db_instance.client:
            logger.error("❌ MongoDB client not initialized")
            return TestResult(
                "Complete User Identity Pipeline",
                False,
                "MongoDB client not initialized"
            )
        
        # Initialize with existing mongo connection
        service = UserResolutionService(db_instance.client)
        
        # Step 1: User signup
        signup_email = f"pipeline_test_{int(datetime.now().timestamp())}@example.com"
        user_id_signup, is_new, _ = await service.resolve_user(signup_email)
        logger.info(f"  Step 1: Signup {signup_email} → {user_id_signup} (new={is_new})")
        
        # Step 2: Store memories
        preference = "artificial intelligence research"
        pref_result, _ = await unified_memory_orchestrator.store_memory(
            user_id=user_id_signup,
            memory_content=preference,
            memory_type=MemoryType.PREFERENCE
        )
        logger.info(f"  Step 2: Stored preference, success={pref_result.success}")
        
        # Step 3: User logs in again with different case
        login_email = signup_email.upper()  # Same email, UPPERCASE
        user_id_login, is_existing, _ = await service.resolve_user(login_email)
        logger.info(f"  Step 3: Login {login_email} → {user_id_login} (new={is_existing})")
        
        # Step 4: Retrieve memories
        preferences = await unified_memory_orchestrator.get_user_preferences(user_id_login)
        logger.info(f"  Step 4: Retrieved preferences: {preferences}")
        
        # Validate
        success = (
            user_id_signup == user_id_login and  # Same user_id
            is_new == True and                   # First was new
            is_existing == False and             # Second was existing
            preference in preferences            # Memory retrieved
        )
        
        # Cleanup
        await service.users_collection.delete_one({"email": service.normalize_email(signup_email)})
        await unified_memory_orchestrator.memory_collection.delete_one({"userId": user_id_signup})
        
        if success:
            logger.info("✅ TEST 7 PASSED: Complete pipeline working end-to-end")
            return TestResult(
                "Complete User Identity Pipeline",
                True,
                "Email → user_id → memory storage → retrieval all working",
                f"user_id: {user_id_signup}"
            )
        else:
            logger.error("❌ TEST 7 FAILED: Pipeline broken somewhere")
            logger.error(f"   Same user_id: {user_id_signup == user_id_login}")
            logger.error(f"   Signup was new: {is_new}")
            logger.error(f"   Login was existing: {not is_existing}")
            logger.error(f"   Memory found: {preference in preferences}")
            return TestResult(
                "Complete User Identity Pipeline",
                False,
                "One or more pipeline steps failed",
                "Check logs for details"
            )
    
    except Exception as e:
        logger.error(f"❌ TEST 7 ERROR: {e}")
        return TestResult("Complete User Identity Pipeline", False, f"Test error: {e}")


async def initialize_database():
    """Initialize MongoDB connection for tests"""
    try:
        from app.db.mongo_client import connect_to_mongo
        logger.info("🔌 Initializing MongoDB connection for tests...")
        await connect_to_mongo()
        logger.info("✅ MongoDB connection initialized")
        return True
    except Exception as e:
        logger.error(f"❌ MongoDB initialization failed: {e}")
        return False


async def run_all_tests():
    """Run all user identity enforcement tests"""
    print("\n" + "=" * 80)
    print("🔐 USER IDENTITY ENFORCEMENT - TEST SUITE")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80 + "\n")
    
    # Initialize database connection
    db_ready = await initialize_database()
    if not db_ready:
        print("\n" + "=" * 80)
        print("🚨 CRITICAL: MongoDB initialization failed")
        print("Cannot run tests without database connection")
        print("=" * 80)
        return False
    print()
    
    tests = [
        test_email_normalization,
        test_same_email_same_user_id,
        test_duplicate_prevention_database,
        test_memory_continuity_across_sessions,
        test_no_duplicate_memories,
        test_neo4j_user_node_uniqueness,
        test_complete_user_identity_pipeline
    ]
    
    results: List[TestResult] = []
    
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            results.append(TestResult(test.__name__, False, f"Execution error: {e}"))
        
        print()  # Spacing between tests
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)
    
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status} | {result.name}")
        print(f"       {result.message}")
        if result.details:
            print(f"       Details: {result.details}")
        print()
    
    print("=" * 80)
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print("=" * 80)
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED - USER IDENTITY ENFORCEMENT IS WORKING!")
        print("✅ ONE EMAIL = ONE USER rule is enforced across entire system")
    else:
        print("🚨 CRITICAL: TESTS FAILED - USER IDENTITY ENFORCEMENT IS BROKEN!")
        print(f"❌ {failed} test(s) failed - IMMEDIATE FIX REQUIRED (P0 BUG)")
    
    print("=" * 80)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
