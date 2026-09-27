import unittest

from models import OrariTraStazioniInput
from pydantic import ValidationError


class InputValidationTests(unittest.TestCase):
    def test_single_digit_time_is_normalized_before_comparison(self):
        value = OrariTraStazioniInput(stazione_a='Roma', stazione_b='Milano', orario_da='9:00')
        self.assertEqual(value.orario_da, '09:00')

    def test_null_limit_is_rejected_instead_of_crashing_handler(self):
        with self.assertRaises(ValidationError):
            OrariTraStazioniInput(stazione_a='Roma', stazione_b='Milano', limite=None)


class ProtocolRegistrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_tools_return_structured_content(self):
        import server
        result = await server.mcp.call_tool('ciuff_stato_fonti', {})
        self.assertFalse(result.is_error)
        self.assertIsNotNone(result.structured_content)
        self.assertIn('sources', result.structured_content)

    async def test_legacy_tools_and_new_multi_operator_tools_are_registered(self):
        import server
        tools = await server.mcp.list_tools()
        names = {tool.name for tool in tools}
        self.assertTrue({'trenitalia_cerca_stazione', 'trenitalia_monitora_partenze',
            'trenitalia_monitora_arrivi', 'trenitalia_traccia_treno',
            'trenitalia_orari_tra_stazioni', 'ciuff_cerca_stazioni',
            'ciuff_cerca_viaggi', 'ciuff_stato_treno', 'ciuff_stato_fonti',
            'ciuff_link_biglietti', 'italo_tabellone'} <= names)
        for tool in tools:
            self.assertTrue(tool.annotations.read_only_hint)
            self.assertFalse(tool.annotations.destructive_hint)


if __name__ == '__main__':
    unittest.main()
