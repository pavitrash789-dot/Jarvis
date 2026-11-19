import unittest
import os
import json
import re

# Set headless / silent mode for testing
os.environ["JARVIS_INPUT"] = "keyboard"
os.environ["JARVIS_SILENT"] = "1"

import jarvis

class TestJarvisCapabilities(unittest.TestCase):

    def test_current_time_date(self):
        result = jarvis.get_current_time_date()
        self.assertIn("The current time is", result)
        self.assertRegex(result, r"\d{1,2}:\d{2}")

    def test_battery_status(self):
        result = jarvis.get_battery_status()
        self.assertTrue(len(result) > 0)
        self.assertTrue(any(term in result.lower() for term in ["battery", "ac power", "status", "%"]))

    def test_hardware_and_system_stats(self):
        ip_res = jarvis.get_ip_address()
        self.assertIn("IP", ip_res)

        disk_res = jarvis.get_disk_space()
        self.assertIn("Disk storage", disk_res)
        self.assertIn("GB", disk_res)

        mem_res = jarvis.get_memory_status()
        self.assertIn("RAM", mem_res)

        sys_res = jarvis.get_system_info()
        self.assertIn("macOS", sys_res)
        self.assertIn("Harshil Sharma", sys_res)

    def test_system_volume_controls(self):
        get_res = jarvis.system_volume("get")
        self.assertIn("volume", get_res.lower())

        max_res = jarvis.system_volume("max")
        self.assertIn("100%", max_res)

        half_res = jarvis.system_volume("half")
        self.assertIn("50%", half_res)

        set_res = jarvis.system_volume("set", "40%")
        self.assertIn("40%", set_res)

    def test_safe_calculate_advanced(self):
        self.assertEqual(jarvis.safe_calculate("25 * 4"), "The answer is 100")
        self.assertEqual(jarvis.safe_calculate("100 plus 50"), "The answer is 150")
        self.assertEqual(jarvis.safe_calculate("200 minus 45"), "The answer is 155")
        self.assertEqual(jarvis.safe_calculate("10 divided by 2"), "The answer is 5")
        self.assertEqual(jarvis.safe_calculate("10 percent of 500"), "The answer is 50")
        self.assertEqual(jarvis.safe_calculate("square root of 144"), "The answer is 12")
        self.assertEqual(jarvis.safe_calculate("5 squared"), "The answer is 25")
        self.assertEqual(jarvis.safe_calculate("2 cubed"), "The answer is 8")
        self.assertEqual(jarvis.safe_calculate("10 modulo 3"), "The answer is 1")
        self.assertIsNone(jarvis.safe_calculate("malicious_code_here()"))

    def test_normalize_command(self):
        # Politeness prefix removal
        self.assertEqual(jarvis.normalize_command("can you please open youtube"), "open youtube")
        self.assertEqual(jarvis.normalize_command("could you tell me the time"), "the time")
        self.assertEqual(jarvis.normalize_command("please take a note buy milk"), "take a note buy milk")
        self.assertEqual(jarvis.normalize_command("i want you to search for jobs"), "search for jobs")

        # Wake word removal while preserving 'jarvis' inside actual questions
        self.assertEqual(jarvis.normalize_command("hey jarvis what time is it"), "what time is it")
        self.assertEqual(jarvis.normalize_command("who is jarvis in iron man"), "who is jarvis in iron man")
        self.assertEqual(jarvis.normalize_command("tell me about jarvis"), "about jarvis")

    def test_notes_management_full_lifecycle(self):
        # Clear notes first
        jarvis.manage_notes("clear")

        # Add notes
        res1 = jarvis.manage_notes("add", "Review portfolio with Pavitra")
        self.assertIn("Review portfolio with Pavitra", res1)

        res2 = jarvis.manage_notes("add", "Prepare interview answers for Python")
        self.assertIn("Prepare interview answers for Python", res2)

        # Show notes
        res3 = jarvis.manage_notes("show")
        self.assertIn("2 notes", res3)

        # Search notes
        search_res = jarvis.manage_notes("search", "Python")
        self.assertIn("Found 1 matching note", search_res)
        self.assertIn("Prepare interview answers for Python", search_res)

        # Delete note
        del_res = jarvis.manage_notes("delete", 1)
        self.assertIn("deleted", del_res.lower())

        show_after_del = jarvis.manage_notes("show")
        self.assertIn("1 note", show_after_del)

        # Cleanup
        jarvis.manage_notes("clear")

    def test_reminders_management_full_lifecycle(self):
        # Clear reminders first
        jarvis.manage_reminders("clear")

        # Add reminders
        res1 = jarvis.manage_reminders("add", "Submit job application by 6 PM")
        self.assertIn("Submit job application by 6 PM", res1)

        res2 = jarvis.manage_reminders("add", "Team sync at 11 AM")
        self.assertIn("Team sync at 11 AM", res2)

        # Show reminders
        res3 = jarvis.manage_reminders("show")
        self.assertIn("2 reminders", res3)

        # Search reminders
        search_res = jarvis.manage_reminders("search", "job application")
        self.assertIn("Found 1 matching reminder", search_res)

        # Delete reminder
        del_res = jarvis.manage_reminders("delete", 1)
        self.assertIn("deleted", del_res.lower())

        # Cleanup
        jarvis.manage_reminders("clear")

    def test_career_profile(self):
        result = jarvis.show_career_profile()
        self.assertIn("B.Com Graduate", result)
        self.assertIn("Finance", result)
        self.assertIn("Python Development", result)

    def test_job_matches(self):
        result = jarvis.show_top_job_matches(limit=3)
        self.assertTrue(len(result) > 0)
        self.assertIn("total jobs", result.lower())

    def test_show_help(self):
        result = jarvis.show_help()
        self.assertIn("capabilities on your screen", result)
        self.assertIn("GMAIL", result)

    def test_execute_ai_action_notes_combined_result(self):
        jarvis.manage_notes("clear")
        ai_resp = '[[ACTION: take_note("Test automated note")]] Right away Sir, I have taken note of that.'
        spoken = jarvis.execute_ai_action(ai_resp)
        self.assertIn("Right away Sir, I have taken note of that.", spoken)
        self.assertIn("Note recorded: 'Test automated note'", spoken)
        notes_output = jarvis.manage_notes("show")
        self.assertIn("Test automated note", notes_output)
        jarvis.manage_notes("clear")

    def test_execute_ai_action_calculation_combined_result(self):
        ai_resp = '[[ACTION: calculate("50 * 20")]] Here is the calculation, Sir.'
        spoken = jarvis.execute_ai_action(ai_resp)
        self.assertIn("Here is the calculation, Sir.", spoken)
        self.assertIn("The answer is 1000", spoken)

    def test_execute_ai_action_battery_combined_result(self):
        ai_resp = '[[ACTION: get_battery()]] Checking your power levels, Sir.'
        spoken = jarvis.execute_ai_action(ai_resp)
        self.assertIn("Checking your power levels, Sir.", spoken)
        self.assertTrue(any(term in spoken.lower() for term in ["battery", "ac power", "status", "%"]))

    def test_offline_knowledge_and_jokes(self):
        who_res = jarvis.get_offline_knowledge("who are you")
        self.assertIn("JARVIS", who_res)
        self.assertIn("Harshil Sharma", who_res)

        joke_res = jarvis.get_offline_knowledge("tell me a joke")
        self.assertTrue(len(joke_res) > 10)

    def test_app_aliases_and_websites(self):
        self.assertIn("vscode", jarvis.APP_ALIASES)
        self.assertEqual(jarvis.APP_ALIASES["vscode"], "Visual Studio Code")
        self.assertIn("chrome", jarvis.APP_ALIASES)
        self.assertEqual(jarvis.APP_ALIASES["chrome"], "Google Chrome")

        self.assertIn("youtube", jarvis.POPULAR_WEBSITES)
        self.assertIn("github", jarvis.POPULAR_WEBSITES)
        self.assertIn("chatgpt", jarvis.POPULAR_WEBSITES)
        self.assertIn("linkedin", jarvis.POPULAR_WEBSITES)

if __name__ == "__main__":
    unittest.main()
