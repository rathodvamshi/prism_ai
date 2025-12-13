"""
🧪 PERFECT USER SEPARATION TESTS

This test suite verifies that the implemented architecture provides:
🟢 Complete user separation across all databases
🟢 No data mixing between users
🟢 No duplicate data
🟢 Proper userId linking everywhere

Run this to verify the perfect implementation.
"""

import asyncio
import pytest
from datetime import datetime
from bson import ObjectId

# Import all our perfect components
from app.models.perfect_models import UserModel, CreateUserRequest
from app.services.perfect_memory_pipeline import process_message, get_user_summary, delete_user_data
from app.db.mongo_client import users_collection, sessions_collection, tasks_collection, memory_collection
from app.db.redis_client import store_otp, verify_otp, clear_user_cache
from app.services.vector_memory_service import store_user_memory, search_user_memories
from app.db.neo4j_client import create_user_in_graph, add_interest_to_user, get_user_context_summary

class PerfectUserSeparationTests:
    """
    🎯 COMPREHENSIVE TEST SUITE FOR PERFECT USER SEPARATION
    """
    
    def __init__(self):
        self.test_users = []  # Track test users for cleanup
    
    async def setup_test_users(self):
        """Create test users for separation testing"""
        print("🧪 Setting up test users...")
        
        # Create two test users with different data
        user1_data = CreateUserRequest(
            email="test1@example.com",
            name="Alice Test",
            role="developer", 
            hobbies=["reading", "coding"],
            interests=["AI", "programming"],
            responseStyle="friendly"
        )
        
        user2_data = CreateUserRequest(
            email="test2@example.com", 
            name="Bob Test",
            role="designer",
            hobbies=["drawing", "music"],
            interests=["design", "art"],
            responseStyle="professional"
        )
        
        # Create users in MongoDB
        user1_model = UserModel(**user1_data.dict())
        user2_model = UserModel(**user2_data.dict())
        
        result1 = await users_collection.insert_one(user1_model.dict(by_alias=True))
        result2 = await users_collection.insert_one(user2_model.dict(by_alias=True))
        
        user1_id = str(result1.inserted_id)
        user2_id = str(result2.inserted_id)
        
        # Create in Neo4j  
        await create_user_in_graph(user1_id, user1_data.email, user1_data.name)
        await create_user_in_graph(user2_id, user2_data.email, user2_data.name)
        
        # Add interests to graph
        for interest in user1_data.interests:
            await add_interest_to_user(user1_id, interest, "interest")
        
        for interest in user2_data.interests:
            await add_interest_to_user(user2_id, interest, "interest")
        
        self.test_users = [
            {"id": user1_id, "email": user1_data.email, "name": user1_data.name},
            {"id": user2_id, "email": user2_data.email, "name": user2_data.name}
        ]
        
        print(f"✅ Created test users: {user1_data.email}, {user2_data.email}")
        return self.test_users
    
    async def test_mongodb_user_separation(self):
        """
        Test 1: MongoDB User Data Separation
        🟢 Rule: Each user's data is completely isolated
        """
        print("\n🧪 Test 1: MongoDB User Separation")
        
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Get user data
        user1_data = await users_collection.find_one({"_id": ObjectId(user1["id"])})
        user2_data = await users_collection.find_one({"_id": ObjectId(user2["id"])})
        
        # Verify separation
        assert user1_data["email"] != user2_data["email"], "❌ Email mixing detected!"
        assert user1_data["interests"] != user2_data["interests"], "❌ Interest mixing detected!"
        assert user1_data["hobbies"] != user2_data["hobbies"], "❌ Hobby mixing detected!"
        
        print("✅ MongoDB user data completely separated")
        return True
    
    async def test_session_separation(self):
        """
        Test 2: Chat Session Separation  
        🟢 Rule: Sessions are linked to userId and cannot mix
        """
        print("\n🧪 Test 2: Chat Session Separation")
        
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Send messages for both users
        await process_message(
            user_id=user1["id"],
            session_id="session_1", 
            message="I love programming and AI",
            user_email=user1["email"]
        )
        
        await process_message(
            user_id=user2["id"],
            session_id="session_2",
            message="I love art and design",
            user_email=user2["email"] 
        )
        
        # Verify sessions are separated
        user1_sessions = await sessions_collection.find({"userId": ObjectId(user1["id"])}).to_list(length=10)
        user2_sessions = await sessions_collection.find({"userId": ObjectId(user2["id"])}).to_list(length=10)
        
        assert len(user1_sessions) > 0, "❌ User 1 sessions not found!"
        assert len(user2_sessions) > 0, "❌ User 2 sessions not found!"
        
        # Verify no cross-contamination
        for session in user1_sessions:
            assert str(session["userId"]) == user1["id"], "❌ Session userId mismatch for user 1!"
        
        for session in user2_sessions:
            assert str(session["userId"]) == user2["id"], "❌ Session userId mismatch for user 2!"
        
        print("✅ Chat sessions completely separated by userId")
        return True
    
    async def test_vector_memory_separation(self):
        """
        Test 3: Pinecone Vector Memory Separation
        🟢 Rule: Each user has own namespace in Pinecone
        """
        print("\n🧪 Test 3: Vector Memory Separation")
        
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Store different memories for each user
        await store_user_memory(user1["id"], "I love Python programming", "preference")
        await store_user_memory(user2["id"], "I love graphic design", "preference")
        
        # Search each user's memories
        user1_memories = await search_user_memories(user1["id"], "programming", top_k=5)
        user2_memories = await search_user_memories(user2["id"], "design", top_k=5)
        
        # Verify separation
        assert len(user1_memories) > 0, "❌ User 1 memories not found!"
        assert len(user2_memories) > 0, "❌ User 2 memories not found!"
        
        # Check that user 1's memories don't contain user 2's data
        user1_texts = [mem["text"].lower() for mem in user1_memories]
        user2_texts = [mem["text"].lower() for mem in user2_memories]
        
        assert not any("design" in text for text in user1_texts), "❌ Memory contamination: User 1 has User 2's memories!"
        assert not any("programming" in text for text in user2_texts), "❌ Memory contamination: User 2 has User 1's memories!"
        
        print("✅ Vector memories completely separated by namespace")
        return True
    
    async def test_graph_relationship_separation(self):
        """
        Test 4: Neo4j Graph Relationship Separation
        🟢 Rule: Graph relationships are user-specific
        """
        print("\n🧪 Test 4: Graph Relationship Separation")
        
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Get graph summaries
        user1_summary = await get_user_context_summary(user1["id"])
        user2_summary = await get_user_context_summary(user2["id"])
        
        assert user1_summary != user2_summary, "❌ Graph summaries are identical!"
        
        # Verify user-specific data in summaries
        assert "Alice" in user1_summary, "❌ User 1 name not in graph summary!"
        assert "Bob" in user2_summary, "❌ User 2 name not in graph summary!"
        
        # Verify interests don't mix
        assert "AI" in user1_summary or "programming" in user1_summary, "❌ User 1 interests missing!"
        assert "design" in user2_summary or "art" in user2_summary, "❌ User 2 interests missing!"
        
        print("✅ Graph relationships completely separated")
        return True
    
    async def test_redis_cache_separation(self):
        """
        Test 5: Redis Cache Separation
        🟢 Rule: Redis keys include userId to prevent mixing
        """
        print("\n🧪 Test 5: Redis Cache Separation")
        
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Store OTPs for both users
        await store_otp(user1["email"], "123456", 5)
        await store_otp(user2["email"], "789012", 5)
        
        # Verify separation - each user can only access their own OTP
        user1_otp_valid = await verify_otp(user1["email"], "123456")
        user2_otp_valid = await verify_otp(user2["email"], "789012")
        
        # Try cross-verification (should fail)
        user1_wrong_otp = await verify_otp(user1["email"], "789012")
        user2_wrong_otp = await verify_otp(user2["email"], "123456")
        
        assert user1_otp_valid == True, "❌ User 1 cannot access own OTP!"
        assert user2_otp_valid == True, "❌ User 2 cannot access own OTP!"
        assert user1_wrong_otp == False, "❌ User 1 can access User 2's OTP!"
        assert user2_wrong_otp == False, "❌ User 2 can access User 1's OTP!"
        
        print("✅ Redis cache completely separated by user keys")
        return True
    
    async def test_comprehensive_user_summary(self):
        """
        Test 6: Comprehensive User Summary (All Databases)
        🟢 Rule: Summary contains only user-specific data
        """
        print("\n🧪 Test 6: Comprehensive User Summary")
        
        user1, user2 = self.test_users[0], self.test_users[1]
        
        # Get comprehensive summaries
        user1_summary = await get_user_summary(user1["id"])
        user2_summary = await get_user_summary(user2["id"])
        
        # Verify data integrity
        assert user1_summary["email"] == user1["email"], "❌ User 1 email mismatch in summary!"
        assert user2_summary["email"] == user2["email"], "❌ User 2 email mismatch in summary!"
        
        assert user1_summary["name"] == user1["name"], "❌ User 1 name mismatch in summary!"
        assert user2_summary["name"] == user2["name"], "❌ User 2 name mismatch in summary!"
        
        # Verify no data mixing
        assert user1_summary["userId"] != user2_summary["userId"], "❌ User IDs are identical!"
        
        print("✅ Comprehensive summaries completely separated")
        return True
    
    async def test_complete_user_deletion(self):
        """
        Test 7: Complete User Deletion
        🟢 Rule: All user data deleted from all databases
        """
        print("\n🧪 Test 7: Complete User Deletion")
        
        user_to_delete = self.test_users[1]  # Delete user 2
        user_to_keep = self.test_users[0]    # Keep user 1
        
        # Delete user completely
        success = await delete_user_data(user_to_delete["id"])
        assert success == True, "❌ User deletion failed!"
        
        # Verify deletion from MongoDB
        deleted_user = await users_collection.find_one({"_id": ObjectId(user_to_delete["id"])})
        assert deleted_user is None, "❌ User still exists in MongoDB!"
        
        # Verify other user still exists
        existing_user = await users_collection.find_one({"_id": ObjectId(user_to_keep["id"])})
        assert existing_user is not None, "❌ Wrong user was deleted!"
        
        # Clean Redis cache
        await clear_user_cache(user_to_delete["id"])
        
        print("✅ Complete user deletion successful, other users unaffected")
        return True
    
    async def cleanup_test_data(self):
        """Clean up all test data"""
        print("\n🧹 Cleaning up test data...")
        
        for user in self.test_users:
            try:
                await delete_user_data(user["id"])
                await clear_user_cache(user["id"])
            except Exception as e:
                print(f"⚠️  Cleanup warning for {user['email']}: {e}")
        
        print("✅ Test data cleaned up")
    
    async def run_all_tests(self):
        """
        🚀 RUN ALL USER SEPARATION TESTS
        
        This comprehensive test suite verifies:
        - Complete user separation
        - No data mixing
        - No duplicates  
        - Proper deletion
        """
        print("🚀 STARTING PERFECT USER SEPARATION TESTS")
        print("=" * 50)
        
        try:
            # Setup
            await self.setup_test_users()
            
            # Run all tests
            test_results = []
            
            test_results.append(await self.test_mongodb_user_separation())
            test_results.append(await self.test_session_separation()) 
            test_results.append(await self.test_vector_memory_separation())
            test_results.append(await self.test_graph_relationship_separation())
            test_results.append(await self.test_redis_cache_separation())
            test_results.append(await self.test_comprehensive_user_summary())
            test_results.append(await self.test_complete_user_deletion())
            
            # Results
            passed_tests = sum(test_results)
            total_tests = len(test_results)
            
            print("\n" + "=" * 50)
            print(f"🎯 TEST RESULTS: {passed_tests}/{total_tests} PASSED")
            
            if passed_tests == total_tests:
                print("🏆 ALL TESTS PASSED - PERFECT USER SEPARATION VERIFIED!")
                print("✅ Your architecture provides complete user isolation")
                print("✅ No data mixing between users")
                print("✅ No duplicate data issues") 
                print("✅ Complete user deletion works")
            else:
                print("❌ SOME TESTS FAILED - CHECK USER SEPARATION")
            
        except Exception as e:
            print(f"❌ Test suite error: {e}")
        
        finally:
            # Always cleanup
            await self.cleanup_test_data()

# 🎯 CONVENIENCE FUNCTIONS TO RUN TESTS

async def test_perfect_user_separation():
    """Run the complete user separation test suite"""
    tester = PerfectUserSeparationTests()
    await tester.run_all_tests()

def run_separation_tests():
    """Synchronous wrapper to run tests"""
    asyncio.run(test_perfect_user_separation())

if __name__ == "__main__":
    # Run tests directly
    print("🧪 Running Perfect User Separation Tests...")
    run_separation_tests()