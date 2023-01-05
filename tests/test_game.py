from unittest import TestCase
from schnapsen.deck import Card, Rank, Suit
from schnapsen.game import (
    Trump_Exchange,
    Marriage,
    Hand,
    Talon,
    Score,
    BotState,
    GameState,
    SchnapsenGamePlayEngine,
    LeaderGameState,
    RegularMove,
    PartialTrick,
    FollowerGameState,
)
from schnapsen.cli import RandBot
import random


class MoveTest(TestCase):
    """Tests the different move types"""

    def setUp(self) -> None:
        self.jacks = []
        for suit in Suit:
            jack = Card.get_card(Rank.JACK, suit)
            self.jacks.append(jack)

    def test_trump_exchange_creation(self) -> None:
        for jack in self.jacks:
            exchange = Trump_Exchange(jack=jack)
            self.assertTrue(exchange.is_trump_exchange())
            self.assertFalse(exchange.is_marriage())
            self.assertEqual(len(exchange.cards), 1)
            self.assertEqual(exchange.cards[0], jack)

    def test_trump_creation_fails(self) -> None:
        for card in Card:
            if card not in self.jacks:
                with self.assertRaises(AssertionError):
                    Trump_Exchange(jack=card)

    def test_marriage_creation_fails(self) -> None:
        for card1 in Card:
            for card2 in Card:
                if not (card1.suit == card2.suit and card1.rank == Rank.QUEEN, card2.rank == Rank.KING):
                    with self.assertRaises(AssertionError):
                        Marriage(queen_card=card1, king_card=card2)

    def test_marriage_creation(self) -> None:
        for suit in Suit:
            queen = Card.get_card(Rank.QUEEN, suit)
            king = Card.get_card(Rank.KING, suit)
            marriage = Marriage(queen_card=queen, king_card=king)
            self.assertTrue(marriage.is_marriage())
            self.assertFalse(marriage.is_trump_exchange())
            self.assertEqual(marriage.as_regular_move().cards[0], queen)
            self.assertEqual(marriage.cards, [queen, king])


class HandTest(TestCase):

    def setUp(self) -> None:
        self.ten_cards = [
            Card.FIVE_CLUBS,
            Card.JACK_HEARTS,
            Card.ACE_SPADES,
            Card.TWO_HEARTS,
            Card.QUEEN_HEARTS,
            # intentional repetition. Hand should not assume uniqueness
            Card.QUEEN_HEARTS,
            Card.JACK_SPADES,
            Card.ACE_HEARTS,
            Card.TWO_CLUBS,
            Card.QUEEN_DIAMONDS,
        ]

    def test_too_large_creation_fail(self) -> None:
        for max_size in range(len(self.ten_cards)):
            for too_large in range(max_size + 1, len(self.ten_cards)):
                too_many_cards = self.ten_cards[:too_large]
                with self.assertRaises(AssertionError):
                    Hand(cards=too_many_cards, max_size=max_size)

    def test_creation(self) -> None:
        for max_size in range(len(self.ten_cards)):
            for created_size in range(max_size):
                start_cards = self.ten_cards[:created_size]
                hand = Hand(start_cards, max_size=max_size)
                if created_size == 0:
                    self.assertTrue(hand.is_empty())
                else:
                    self.assertFalse(hand.is_empty())

    def test_removal_unique(self) -> None:
        hand = Hand(self.ten_cards[:5])
        self.assertIn(Card.FIVE_CLUBS, hand)
        hand.remove(Card.FIVE_CLUBS)
        self.assertNotIn(Card.FIVE_CLUBS, hand)

    def test_removal_duplicate(self) -> None:
        hand = Hand(self.ten_cards, max_size=10)
        self.assertIn(Card.QUEEN_HEARTS, hand)
        hand.remove(Card.QUEEN_HEARTS)
        self.assertIn(Card.QUEEN_HEARTS, hand)
        # remove the second one
        hand.remove(Card.QUEEN_HEARTS)
        self.assertNotIn(Card.QUEEN_HEARTS, hand)

    def test_remove_non_existing(self) -> None:
        hand = Hand(self.ten_cards, max_size=10)
        for card in Card:
            if card not in self.ten_cards:
                with self.assertRaises(Exception):
                    hand.remove(card)

    def test_add(self) -> None:
        hand = Hand(self.ten_cards[:4], max_size=5)
        hand.add(Card.KING_SPADES)
        self.assertEqual(
            hand.cards,
            [
                Card.FIVE_CLUBS,
                Card.JACK_HEARTS,
                Card.ACE_SPADES,
                Card.TWO_HEARTS,
                Card.KING_SPADES,
            ],
        )

    def test_add_too_much(self) -> None:
        hand = Hand(self.ten_cards[:4], max_size=5)
        hand.add(Card.EIGHT_CLUBS)
        with self.assertRaises(AssertionError):
            hand.add(Card.FIVE_HEARTS)

    def test_has_cards(self) -> None:
        hand = Hand(self.ten_cards, max_size=10)
        self.assertTrue(hand.has_cards([Card.JACK_HEARTS, Card.TWO_HEARTS]))

    def test_copy(self) -> None:
        hand = Hand(self.ten_cards, max_size=10)
        copy = hand.copy()
        self.assertEqual(copy.get_cards(), hand.get_cards())
        # modifying the copy must not modify the original
        copy.remove(Card.FIVE_CLUBS)
        self.assertEqual(hand.get_cards(), self.ten_cards)

    def test_filter_suit(self) -> None:
        hand = Hand(self.ten_cards, max_size=10)
        self.assertEqual(
            hand.filter_suit(Suit.HEARTS),
            [Card.JACK_HEARTS, Card.TWO_HEARTS, Card.QUEEN_HEARTS, Card.QUEEN_HEARTS, Card.ACE_HEARTS],
        )
        self.assertEqual(hand.filter_suit(Suit.SPADES), [Card.ACE_SPADES, Card.JACK_SPADES])
        self.assertEqual(hand.filter_suit(Suit.CLUBS), [Card.FIVE_CLUBS, Card.TWO_CLUBS])
        self.assertEqual(hand.filter_suit(Suit.DIAMONDS), [Card.QUEEN_DIAMONDS])

    def test_filter_rank(self) -> None:
        hand = Hand(self.ten_cards, max_size=10)
        self.assertEqual(hand.filter_rank(Rank.ACE), [Card.ACE_SPADES, Card.ACE_HEARTS])
        self.assertEqual(hand.filter_rank(Rank.TWO), [Card.TWO_HEARTS, Card.TWO_CLUBS])
        self.assertEqual(hand.filter_rank(Rank.JACK), [Card.JACK_HEARTS, Card.JACK_SPADES])
        self.assertEqual(hand.filter_rank(Rank.QUEEN), [Card.QUEEN_HEARTS, Card.QUEEN_HEARTS, Card.QUEEN_DIAMONDS])
        self.assertEqual(hand.filter_rank(Rank.KING), [])
        self.assertEqual(hand.filter_rank(Rank.THREE), [])


class GameTest(TestCase):

    def test_Talon(self) -> None:
        foo = Talon(cards=[Card.ACE_CLUBS], trump_suit=Suit.CLUBS)
        with self.assertRaises(AssertionError):
            foo.trump_exchange(Card.JACK_CLUBS)

        foo = Talon(cards=[Card.ACE_CLUBS, Card.TWO_CLUBS], trump_suit=Suit.CLUBS)
        with self.assertRaises(AssertionError):
            foo.trump_exchange(Card.JACK_DIAMONDS)

        foo = Talon(cards=[Card.ACE_CLUBS, Card.TWO_CLUBS], trump_suit=Suit.CLUBS)
        bar = foo.trump_exchange(new_trump=Card.JACK_CLUBS)
        self.assertEqual(bar, Card.TWO_CLUBS)
        with self.assertRaises(AssertionError):
            foo.draw_cards(3)
        baz = list(foo.draw_cards(1))
        self.assertEqual(baz[0], Card.ACE_CLUBS)
        self.assertEqual(foo._cards, [Card.JACK_CLUBS])
        self.assertEqual(foo.trump_suit(), Suit.CLUBS)

    def test_Score(self) -> None:

        randnum0 = random.randint(0, 10)
        randnum1 = random.randint(0, 10)
        randnum2 = random.randint(0, 10)
        randnum3 = random.randint(0, 10)

        foo = Score(direct_points=randnum0, pending_points=randnum1)
        bar = Score(direct_points=randnum2, pending_points=randnum3)

        baz = foo.__add__(bar)
        self.assertEqual(baz.direct_points, randnum0 + randnum2)
        self.assertEqual(baz.pending_points, randnum1 + randnum3)

        qux = baz.copy()
        self.assertEqual(baz, qux)
        quux = qux.redeem_pending_points()
        self.assertEqual(quux.direct_points, randnum0 + randnum1 + randnum2 + randnum3)
        self.assertEqual(quux.pending_points, 0)

    def test_BotState(self) -> None:
        bot = RandBot(seed=42)
        hand = Hand(
            cards=[Card.ACE_CLUBS, Card.FIVE_CLUBS, Card.NINE_HEARTS, Card.SEVEN_CLUBS]
        )
        bot_id = "foo"
        score = Score(direct_points=4, pending_points=2)
        won_cards = [Card.ACE_DIAMONDS]
        foo = BotState(
            implementation=bot,
            hand=hand,
            bot_id=bot_id,
            score=score,
            won_cards=won_cards,
        )
        bar = foo.copy()
        self.assertEqual(bar.implementation, bot)
        self.assertEqual(bar.hand.cards, hand.cards)
        self.assertEqual(bar.bot_id, bot_id)
        self.assertEqual(bar.score, score)
        self.assertEqual(bar.won_cards, won_cards)

    def test_GameState(self) -> None:
        bot0 = RandBot(seed=42)
        hand0 = Hand(
            cards=[Card.ACE_CLUBS, Card.FIVE_CLUBS, Card.NINE_HEARTS, Card.SEVEN_CLUBS]
        )
        bot_id0 = "0"
        score0 = Score(direct_points=4, pending_points=2)
        won_cards0 = [Card.ACE_DIAMONDS]
        leader = BotState(
            implementation=bot0,
            hand=hand0,
            bot_id=bot_id0,
            score=score0,
            won_cards=won_cards0,
        )

        bot1 = RandBot(seed=43)
        hand1 = Hand(
            cards=[
                Card.ACE_SPADES,
                Card.FIVE_HEARTS,
                Card.NINE_CLUBS,
                Card.SEVEN_SPADES,
            ]
        )
        bot_id1 = "1"
        score1 = Score(direct_points=2, pending_points=4)
        won_cards1 = [Card.NINE_DIAMONDS]
        follower = BotState(
            implementation=bot1,
            hand=hand1,
            bot_id=bot_id1,
            score=score1,
            won_cards=won_cards1,
        )
        talon = Talon(cards=[Card.ACE_HEARTS], trump_suit=Suit.HEARTS)

        gs = GameState(
            leader=leader, follower=follower, talon=talon, previous=None
        )
        self.assertFalse(gs.all_cards_played())

    def test_LeaderGameState(self) -> None:
        bot0 = RandBot(seed=42)
        hand0 = Hand(
            cards=[Card.ACE_CLUBS, Card.FIVE_CLUBS, Card.NINE_HEARTS, Card.SEVEN_CLUBS]
        )
        bot_id0 = "0"
        score0 = Score(direct_points=4, pending_points=2)
        won_cards0 = [Card.ACE_DIAMONDS]
        leader = BotState(
            implementation=bot0,
            hand=hand0,
            bot_id=bot_id0,
            score=score0,
            won_cards=won_cards0,
        )

        bot1 = RandBot(seed=43)
        hand1 = Hand(
            cards=[
                Card.ACE_SPADES,
                Card.FIVE_HEARTS,
                Card.NINE_CLUBS,
                Card.SEVEN_SPADES,
            ]
        )
        bot_id1 = "1"
        score1 = Score(direct_points=2, pending_points=4)
        won_cards1 = [Card.NINE_DIAMONDS]
        follower = BotState(
            implementation=bot1,
            hand=hand1,
            bot_id=bot_id1,
            score=score1,
            won_cards=won_cards1,
        )
        talon = Talon(cards=[Card.ACE_HEARTS], trump_suit=Suit.HEARTS)

        gs = GameState(
            leader=leader, follower=follower, talon=talon, previous=None
        )
        sgpe = SchnapsenGamePlayEngine()
        lgs = LeaderGameState(state=gs, engine=sgpe)
        self.assertEqual(
            lgs.valid_moves(),
            [
                RegularMove(Card.ACE_CLUBS),
                RegularMove(Card.FIVE_CLUBS),
                RegularMove(Card.NINE_HEARTS),
                RegularMove(Card.SEVEN_CLUBS),
            ],
        )
        self.assertEqual(
            lgs.get_hand().cards,
            [
                Card.ACE_CLUBS,
                Card.FIVE_CLUBS,
                Card.NINE_HEARTS,
                Card.SEVEN_CLUBS,
            ],
        )

    def test_FollowerGameState(self) -> None:
        bot0 = RandBot(seed=42)
        hand0 = Hand(
            cards=[Card.ACE_CLUBS, Card.FIVE_CLUBS, Card.NINE_HEARTS, Card.SEVEN_CLUBS]
        )
        bot_id0 = "0"
        score0 = Score(direct_points=4, pending_points=2)
        won_cards0 = [Card.ACE_DIAMONDS]
        leader = BotState(
            implementation=bot0,
            hand=hand0,
            bot_id=bot_id0,
            score=score0,
            won_cards=won_cards0,
        )

        bot1 = RandBot(seed=43)
        hand1 = Hand(
            cards=[
                Card.ACE_SPADES,
                Card.FIVE_HEARTS,
                Card.NINE_CLUBS,
                Card.SEVEN_SPADES,
            ]
        )
        bot_id1 = "1"
        score1 = Score(direct_points=2, pending_points=4)
        won_cards1 = [Card.NINE_DIAMONDS]
        follower = BotState(
            implementation=bot1,
            hand=hand1,
            bot_id=bot_id1,
            score=score1,
            won_cards=won_cards1,
        )
        talon = Talon(cards=[Card.ACE_HEARTS], trump_suit=Suit.HEARTS)

        gs = GameState(
            leader=leader, follower=follower, talon=talon, previous=None
        )
        sgpe = SchnapsenGamePlayEngine()

        te = Trump_Exchange(jack=Card.JACK_SPADES)
        mv = RegularMove(Card.ACE_CLUBS)
        pt = PartialTrick(trump_exchange=te, leader_move=mv)
        # TODO lgs should be tested as well
        # lgs = LeaderGameState(state=gs, engine=sgpe)
        fgs = FollowerGameState(state=gs, engine=sgpe, partial_trick=pt)
        self.assertEqual(
            fgs.valid_moves(),
            [
                RegularMove(Card.ACE_SPADES),
                RegularMove(Card.FIVE_HEARTS),
                RegularMove(Card.NINE_CLUBS),
                RegularMove(Card.SEVEN_SPADES),
            ],
        )
        self.assertEqual(
            fgs.get_hand().cards,
            [
                Card.ACE_SPADES,
                Card.FIVE_HEARTS,
                Card.NINE_CLUBS,
                Card.SEVEN_SPADES,
            ],
        )

    def test_marriage_point(self) -> None:
        # make game
        # play marriage
        # loose trick
        # make sure marriage points are not applied
        #        assert
        # win trick

        # make sure marriage poits are applied
        #        assert
        pass
