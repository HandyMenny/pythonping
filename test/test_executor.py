import collections
import unittest
from pythonping import executor
from pythonping import icmp


class SuccessfulResponseMock(executor.Response):
    """Mock a successful response to a ping"""
    @property
    def success(self):
        return True


class FailingResponseMock(executor.Response):
    """Mock a failed response to a ping"""
    @property
    def success(self):
        return False


class ExecutorUtilsTestCase(unittest.TestCase):
    """Tests for standalone functions in pythonping.executor"""

    def test_represent_seconds_in_ms(self):
        """Verifies conversion from seconds to milliseconds works correctly"""
        self.assertEqual(executor.represent_seconds_in_ms(4), 4000, 'Failed to convert seconds to milliseconds')
        self.assertEqual(executor.represent_seconds_in_ms(0), 0, 'Failed to convert seconds to milliseconds')
        self.assertEqual(executor.represent_seconds_in_ms(0.001), 1, 'Failed to convert seconds to milliseconds')
        self.assertEqual(executor.represent_seconds_in_ms(0.0001), 0.1, 'Failed to convert seconds to milliseconds')
        self.assertEqual(executor.represent_seconds_in_ms(0.00001), 0.01, 'Failed to convert seconds to milliseconds')


class ResponseTestCase(unittest.TestCase):
    """Tests to verify that a Response object renders information correctly"""

    @staticmethod
    def craft_response_of_type(response_type):
        """Generates an executor.Response from an icmp.Types

        :param response_type: Type of response
        :type response_type: Union[icmp.Type, tuple]
        :return: The crafted response
        :rtype: executor.Response"""
        return executor.Response(executor.Message('', icmp.ICMP(response_type), '127.0.0.1'), 0.1)

    def test_success(self):
        """Verifies the if the Response can indicate a success to a request correctly"""
        self.assertTrue(self.craft_response_of_type(icmp.Types.EchoReply).success,
                        'Unable to validate a successful response')
        self.assertFalse(self.craft_response_of_type(icmp.Types.DestinationUnreachable).success,
                         'Unable to validate Destination Unreachable')
        self.assertFalse(self.craft_response_of_type(icmp.Types.BadIPHeader).success,
                         'Unable to validate Bad IP Header')
        self.assertFalse(executor.Response(None, 0.1).success, 'Unable to validate timeout (no payload)')

    def test_error_message(self):
        """Verifies error messages are presented correctly"""
        self.assertEqual(self.craft_response_of_type(icmp.Types.EchoReply).error_message, None,
                         'Generated error message when response was correct')
        self.assertEqual(self.craft_response_of_type(icmp.Types.DestinationUnreachable).error_message,
                         'Network Unreachable',
                         'Unable to classify a Network Unreachable error correctly')
        self.assertEqual(executor.Response(None, 0.1).error_message, 'No response',
                         'Unable to generate correct message when response is not received')
        pass

    def time_elapsed(self):
        """Verifies the time elapsed is presented correctly"""
        self.assertEqual(executor.Response(None, 1).time_elapsed_ms, 1000, 'Bad ms representation for 1 second')
        self.assertEqual(executor.Response(None, 0.001).time_elapsed_ms, 1, 'Bad ms representation for 1 ms')
        self.assertEqual(executor.Response(None, 0.01).time_elapsed_ms, 10, 'Bad ms representation for 10 ms')


class ResponseListTestCase(unittest.TestCase):
    """Tests for ResponseList"""

    @staticmethod
    def responses_from_times_success(times):
        """Generates a list of successful responses from a list of time elapsed

        :param times: List of time elapsed for each response
        :type times: list
        :return: List of responses
        :rtype: executor.ResponseList"""
        return executor.ResponseList([SuccessfulResponseMock(None, _) for _ in times])

    @staticmethod
    def responses_from_times_failed(times):
        """Generates a list of failing responses from a list of time elapsed

        :param time_messages: List of [time,message] time is elapsed for each response,
        message is error message
        :type times: list
        :return: List of responses
        :rtype: executor.ResponseList"""

        return executor.ResponseList([FailingResponseMock(None, _) for _ in times])

    def test_rtt_min_ms(self):
        """Verifies the minimum RTT is found correctly"""
        self.assertEqual(
            self.responses_from_times_success([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).rtt_min,
            0,
            'Unable to identify minimum RTT of 0'
        )
        self.assertEqual(
            self.responses_from_times_success([38, 11, 93, 100, 38, 11, 0.1]).rtt_min,
            0.1,
            'Unable to identify minimum RTT of 0.1'
        )
        self.assertEqual(
            self.responses_from_times_success([10, 10, 10, 10]).rtt_min,
            10,
            'Unable to identify minimum RTT of 10 on a series of only 10s'
        )

    def test_rtt_max_ms(self):
        """Verifies the maximum RTT is found correctly"""
        self.assertEqual(
            self.responses_from_times_success([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).rtt_max,
            9,
            'Unable to identify maximum RTT of 9'
        )
        self.assertEqual(
            self.responses_from_times_success([38, 11, 93, 100, 38, 11, 0.1]).rtt_max,
            100,
            'Unable to identify maximum RTT of 100'
        )
        self.assertEqual(
            self.responses_from_times_success([10, 10, 10, 10]).rtt_max,
            10,
            'Unable to identify maximum RTT of 10 on a series of only 10s'
        )

    def test_rtt_avg_ms(self):
        """Verifies the average RTT is found correctly"""
        self.assertEqual(
            self.responses_from_times_success([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).rtt_avg,
            4.5,
            'Unable to identify average RTT of 4.5'
        )
        self.assertEqual(
            self.responses_from_times_success([38, 11, 93, 100, 38, 11, 0.1]).rtt_avg,
            41.58571428571429,
            'Unable to identify average RTT of 41.58571428571429'
        )
        self.assertEqual(
            self.responses_from_times_success([10, 10, 10, 10]).rtt_avg,
            10,
            'Unable to identify average RTT of 10 on a series of only 10s'
        )

    def test_len(self):
        """Verifies the length is returned correctly"""
        self.assertEqual(
            len(self.responses_from_times_success(list(range(10)))),
            10,
            'Unable identify the length of 10'
        )
        self.assertEqual(
            len(self.responses_from_times_success(list(range(0)))),
            0,
            'Unable identify the length of 0'
        )
        self.assertEqual(
            len(self.responses_from_times_success(list(range(23)))),
            23,
            'Unable identify the length of 23'
        )

    def test_iterable(self):
        """Verifies it is iterable"""
        self.assertTrue(
            isinstance(self.responses_from_times_success([0, 1, 2, 3]), collections.abc.Iterable),
            'Unable to iterate over ResponseList object'
        )

    def test_success_all_success(self):
        """Verify success is calculated correctly if all responses are successful"""
        rs = executor.ResponseList([
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1)
        ])
        self.assertTrue(
            rs.success(executor.SuccessOn.One),
            'Unable to calculate success on one correctly with all responses successful'
        )
        self.assertTrue(
            rs.success(executor.SuccessOn.Most),
            'Unable to calculate success on most with all responses successful'
        )
        self.assertTrue(
            rs.success(executor.SuccessOn.All),
            'Unable to calculate success on all with all responses successful'
        )

    def test_success_one_success(self):
        """Verify success is calculated correctly if one response is successful"""
        rs = executor.ResponseList([
            SuccessfulResponseMock(None, 1),
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1)
        ])
        self.assertTrue(
            rs.success(executor.SuccessOn.One),
            'Unable to calculate success on one correctly with one response successful'
        )
        self.assertFalse(
            rs.success(executor.SuccessOn.Most),
            'Unable to calculate success on most with one response successful'
        )
        self.assertFalse(
            rs.success(executor.SuccessOn.All),
            'Unable to calculate success on all with one response successful'
        )

    def test_success_most_success(self):
        """Verify success is calculated correctly if most responses are successful"""
        rs = executor.ResponseList([
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            FailingResponseMock(None, 1)
        ])
        self.assertTrue(
            rs.success(executor.SuccessOn.One),
            'Unable to calculate success on one correctly with most responses successful'
        )
        self.assertTrue(
            rs.success(executor.SuccessOn.Most),
            'Unable to calculate success on most with most responses successful'
        )
        self.assertFalse(
            rs.success(executor.SuccessOn.All),
            'Unable to calculate success on all with most responses successful'
        )

    def test_success_half_success(self):
        """Verify success is calculated correctly if half responses are successful"""
        rs = executor.ResponseList([
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1)
        ])
        self.assertTrue(
            rs.success(executor.SuccessOn.One),
            'Unable to calculate success on one correctly with half responses successful'
        )
        self.assertFalse(
            rs.success(executor.SuccessOn.Most),
            'Unable to calculate success on most with half responses successful'
        )
        self.assertFalse(
            rs.success(executor.SuccessOn.All),
            'Unable to calculate success on all with half responses successful'
        )

    def test_no_packets_lost(self):
        rs = executor.ResponseList([
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1)
        ])

        self.assertEqual(
            rs.packet_loss, 
            0.0, 
            "Unable to calculate packet loss correctly when all responses successful"
        )

    def test_all_packets_lost(self):
        rs = executor.ResponseList([
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1)
        ])

        self.assertEqual(
            rs.packet_loss, 
            1.0, 
            "Unable to calculate packet loss correctly when all responses failed"
        )

    def test_some_packets_lost(self):
        rs = executor.ResponseList([
            SuccessfulResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            FailingResponseMock(None, 1),
            FailingResponseMock(None, 1)
        ])

        self.assertEqual(
            rs.packet_loss, 
            0.5, 
            "Unable to calculate packet loss correctly when some of the responses failed"
        )

    def test_some_packets_lost_mixed(self):
        rs = executor.ResponseList([
            FailingResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
            FailingResponseMock(None, 1),
            SuccessfulResponseMock(None, 1),
        ])

        self.assertEqual(
            rs.packet_loss,
            0.5,
            "Unable to calculate packet loss correctly when failing responses are mixed with successful responses"
        )

    def test_rtt_max_ms_lost(self):
        """Verifies the maximum RTT is found correctly even with lost packets"""
        self.assertEqual(
            self.responses_from_times_failed([0, 1, 2, 3, 4, 5, 6, 7, 8, 9]).rtt_max,
            0,
            'Unable to identify maximum RTT of 0 when all packets are lost'
        )
        test = executor.ResponseList(
            self.responses_from_times_failed([2000, 2000, 2000])._responses + self.responses_from_times_success(
                [100, 38, 11, 0.1])._responses)
        self.assertEqual(
            test.rtt_max,
            100,
            'Unable to identify maximum RTT of 100 when half packets are lost'
        )
        test = executor.ResponseList(
            self.responses_from_times_success([10])._responses + self.responses_from_times_failed(
                [2000])._responses + self.responses_from_times_success(
                [10, 10])._responses)
        self.assertEqual(
            test.rtt_max,
            10,
            'Unable to identify maximum RTT of 10 when some packets are lost'
        )

    def test_rtt_avg_ms_lost(self):
        """Verifies the average RTT is found correctly even with lost packets"""
        test = executor.ResponseList(self.responses_from_times_failed(
            [2000, 2000, 2000, 2000, 2000])._responses + self.responses_from_times_success(
            [1, 3, 5, 7, 9])._responses)
        self.assertEqual(
            test.rtt_avg,
            5,
            'Unable to identify average RTT of 5 when half the packets are lost'
        )
        test = executor.ResponseList(
            self.responses_from_times_success([38])._responses + self.responses_from_times_failed(
                [2000])._responses + self.responses_from_times_success(
                [93, 100, 38, 11, 0.1])._responses)
        self.assertEqual(
            test.rtt_avg,
            46.68333333333334,
            'Unable to identify average RTT of 46.68333333333334 when some packets are lost'
        )
        self.assertEqual(
            self.responses_from_times_failed([10, 10, 10, 10]).rtt_avg,
            10,
            'Unable to identify average RTT of 0 when all packets are lost'
        )

    def test_rtt_min_ms_lost(self):
        """Verifies the minimum RTT is found correctly even with lost packets"""
        test = executor.ResponseList(
            self.responses_from_times_failed([2000, 2000])._responses + self.responses_from_times_success(
                [2, 3, 4, 5])._responses +
            self.responses_from_times_failed([2000, 2000, 2000, 2000])._responses)
        self.assertEqual(
            test.rtt_min,
            2,
            'Unable to identify minimum RTT of 2 when some packets are lost'
        )
        self.assertEqual(
            self.responses_from_times_failed([2000, 2000, 2000, 2000, 2000, 2000, 2000]).rtt_min,
            0,
            'Unable to identify minimum RTT of 0 when all packets are lost'
        )
        test = executor.ResponseList(
            self.responses_from_times_failed([2000, 2000])._responses + self.responses_from_times_success(
                [10, 10])._responses)
        self.assertEqual(
            self.responses_from_times_success([10, 10, 10, 10]).rtt_min,
            10,
            'Unable to identify minimum RTT of 10 when half packets are lost'
        )

class CommunicatorTestCase(unittest.TestCase):
    """Tests for Communicator"""

    def test_increase_seq(self):
        """Verifies Communicator can increase sequence number correctly"""
        self.assertEqual(executor.Communicator.increase_seq(1), 2, 'Increasing sequence number 1 did not return 2')
        self.assertEqual(executor.Communicator.increase_seq(100), 101, 'Increasing sequence number 1 did not return 2')
        self.assertEqual(executor.Communicator.increase_seq(0xFFFF), 1,
                         'Not returned to 1 when exceeding sequence number maximum length')
        self.assertEqual(executor.Communicator.increase_seq(0xFFFE), 0xFFFF,
                         'Increasing sequence number 0xFFFE did not return 0xFFFF')
