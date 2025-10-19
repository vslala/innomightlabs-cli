from typing import Any
from unittest.mock import patch, Mock
from prompt_toolkit.formatted_text import FormattedText


class TestMainModule:
    """Test cases for main.py module functions."""

    def test_build_bottom_toolbar(self, mock_planner_agent: Mock) -> None:
        """Test that build_bottom_toolbar returns proper FormattedText with usage metrics."""
        # Given: 
        # Set up mock agent usage data
        mock_planner_agent.usage_totals = {
            'total_tokens': 150,
            'input_tokens': 100, 
            'output_tokens': 50
        }
        mock_planner_agent.last_usage = {
            'total_tokens': 30,
            'input_tokens': 20,
            'output_tokens': 10
        }
        
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # When:
        # Call the test function 
        result = main.build_bottom_toolbar()
        
        # Then: 
        # Verify FormattedText is returned
        assert isinstance(result, FormattedText)
        
        # Verify usage data is included in the toolbar
        toolbar_text = str(result)
        assert '150' in toolbar_text  # total tokens
        assert '100' in toolbar_text  # input tokens
        assert '50' in toolbar_text   # output tokens

    def test_display_banner(self, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test that display_banner outputs welcome content."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Call the function
        main.display_banner()
        
        # Capture the output
        captured = capsys.readouterr()
        output = captured.out
        
        # Verify welcome content was printed
        assert 'INNOMIGHT LABS CLI' in output
        assert 'Your AI-powered coding assistant' in output
        assert 'Type your commands below' in output

    @patch('main.prompt')
    @patch('main.console')
    def test_main_keyboard_interrupt(self, mock_console: Mock, mock_prompt: Mock, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test that KeyboardInterrupt causes graceful exit from main()."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Mock prompt to raise KeyboardInterrupt on first call
        mock_prompt.side_effect = KeyboardInterrupt()
        
        # Call main() - should exit gracefully without raising exception
        main.main()
        
        # Verify prompt was called (attempted to get user input)
        mock_prompt.assert_called_once()
        
        # Verify console.print was called with goodbye message
        mock_console.print.assert_called_with("\n\nGoodbye!", style="bold green")
    @patch('main.prompt')
    @patch('main.console')
    def test_main_empty_input(self, mock_console: Mock, mock_prompt: Mock, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test that empty inputs are skipped and don't call planner_agent.send_message."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Mock prompt to return empty inputs, then KeyboardInterrupt to exit
        mock_prompt.side_effect = ["", "   ", KeyboardInterrupt()]
        
        # Call main() - should skip empty inputs and exit gracefully
        main.main()
        
        # Verify prompt was called multiple times (for empty inputs + KeyboardInterrupt)
        assert mock_prompt.call_count == 3
        
        # Verify planner_agent.send_message was never called (empty inputs skipped)
        mock_planner_agent.send_message.assert_not_called()
    @patch('main.prompt')
    @patch('main.console')
    def test_main_happy_path(self, mock_console: Mock, mock_prompt: Mock, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test normal user input flow with multiple interactions and agent responses."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Configure mock responses
        mock_planner_agent.send_message.side_effect = ["Response 1", "Response 2"]
        mock_prompt.side_effect = ["hello", "how are you?", KeyboardInterrupt()]
        
        # Call main() - should process inputs and exit gracefully
        main.main()
        
        # Verify prompt was called for each input + KeyboardInterrupt
        assert mock_prompt.call_count == 3
        
        # Verify planner_agent.send_message was called for non-empty inputs
        assert mock_planner_agent.send_message.call_count == 2
        mock_planner_agent.send_message.assert_any_call("hello")
        mock_planner_agent.send_message.assert_any_call("how are you?")
        
        # Verify console.print was called with responses and goodbye message
        mock_console.print.assert_any_call("Response 1")
        mock_console.print.assert_any_call("Response 2")
        mock_console.print.assert_called_with("\n\nGoodbye!", style="bold green")

    @patch('main.prompt')
    @patch('main.console')
    def test_main_eof_error(self, mock_console: Mock, mock_prompt: Mock, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test Ctrl+D (EOFError) graceful exit handling."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Mock prompt to raise EOFError on first call
        mock_prompt.side_effect = EOFError()
        
        # Call main() - should exit gracefully without raising exception
        main.main()
        
        # Verify prompt was called (attempted to get user input)
        mock_prompt.assert_called_once()
        
        # Verify planner_agent.send_message was never called
        mock_planner_agent.send_message.assert_not_called()
        
        # Verify console.print was called with goodbye message
        mock_console.print.assert_called_with("\n\nGoodbye!", style="bold green")

    @patch('main.prompt')
    @patch('main.console')
    def test_main_exception_handling(self, mock_console: Mock, mock_prompt: Mock, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test error recovery when agent.send_message() raises exceptions."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Configure mock to raise exception then work normally
        mock_planner_agent.send_message.side_effect = [Exception("Test error"), "Success response"]
        mock_prompt.side_effect = ["first input", "second input", KeyboardInterrupt()]
        
        # Call main() - should handle exception and continue
        main.main()
        
        # Verify prompt was called for all inputs + KeyboardInterrupt
        assert mock_prompt.call_count == 3
        
        # Verify planner_agent.send_message was called twice
        assert mock_planner_agent.send_message.call_count == 2
        mock_planner_agent.send_message.assert_any_call("first input")
        mock_planner_agent.send_message.assert_any_call("second input")
        
        # Verify error message and success response were printed
        mock_console.print.assert_any_call("\n[red]Error: Test error[/red]\n")
        mock_console.print.assert_any_call("Success response")
        mock_console.print.assert_called_with("\n\nGoodbye!", style="bold green")

    @patch('main.prompt')
    @patch('main.console')
    def test_agent_integration(self, mock_console: Mock, mock_prompt: Mock, mock_planner_agent: Mock, capsys: Any) -> None:
        """Test direct agent mock interactions and response handling."""
        # Import main after fixture is set up
        import main
        
        # Override the global planner_agent with our mock
        main.planner_agent = mock_planner_agent
        
        # Configure mock agent response
        mock_planner_agent.send_message.return_value = "Agent response"
        mock_prompt.side_effect = ["test message", KeyboardInterrupt()]
        
        # Call main() - should interact with agent
        main.main()
        
        # Verify agent interaction
        mock_planner_agent.send_message.assert_called_once_with("test message")
        
        # Verify response handling
        mock_console.print.assert_any_call("Agent response")
        mock_console.print.assert_called_with("\n\nGoodbye!", style="bold green")


        
        # Verify console.print was called with goodbye message on KeyboardInterrupt
        mock_console.print.assert_called_with("\n\nGoodbye!", style="bold green")




